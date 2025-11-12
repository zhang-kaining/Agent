# 对话系统上下文管理架构

## 核心架构
多模型+多阶段决策流程：
```
用户输入 → 意图识别 → 更新会话状态 → 触发总结 → 生成Prompt → 调用LLM → 返回结果
```

## 一、意图识别策略

### 1. 初创公司快速验证阶段
- 直接使用主要模型处理

### 2. 成熟公司方案
使用微调BERT的intent模型：
- **优点**：有标注数据时表现良好，部署门槛低
- **缺点**：对新意图或开放意图支持不好

### 3. 基于LLM+RAG的意图识别
- 将意图示例Embedding存储到向量库
- 用户问题Embedding与示例检索后，由LLM判断
- **优点**：灵活，对少样本、新意图支持好，便于动态扩展
- **缺点**：需要调用LLM，速度可能较慢，需要设计RAG

### 4. 混合方案（推荐）
先用intent模型（微调BERT），得分低时再用LLM+RAG识别

## 二、会话状态管理

### 基础会话状态结构
```json
{
    "session_id": "session_id",
    "short_term_memory": {
        "recent_messages": [],
        "conversation_summary": ""
    },
    "long_term_memory": {},
    "intent": "",
    "topic": "",
    "user_profile": {},
    "preference": {},
    "last_user_message": "",
    "update_time": "2023-05-18 10:00:00"
}
```

### 短期记忆管理策略
- **意图一致时**：继续累积短期记忆，不清空上下文
- **达到阈值时**：通过Summary Model自动压缩，更新conversation_summary，清空recent_messages
- **意图/话题切换时**：执行上下文清理、切换stage或重建新task session

### 异步总结机制
- 意图切换后不立即总结
- 由Memory Manager根据以下因素异步触发：
  - 意图变化
  - topic距离
  - 短期记忆长度
  - 系统延迟预算
- 意图识别用轻量模型，summarization用更强的大模型，两者解耦
- 总结任务与主模型回复并行执行，不阻塞用户体验

### 两层Memory架构
**短期记忆（Short-term Memory）**：
- recent_messages：最近几轮对话
- conversation_summary：短期摘要，保留核心内容

**长期记忆（Long-term Memory）**：
- 存储跨多轮甚至跨会话的稳定信息
- 内容：用户偏好、历史任务、重要事实、槽位信息
- 生成方式：结构化JSON、压缩summary或embedding向量
- 触发时机：意图切换、话题切换或短期消息累积到阈值
- 异步生成，保证实时性

**信息不丢失机制**：
清空recent_messages前，先用LLM或轻量summary模块将重要信息压缩到summary或context中，结合summary和短期消息生成回复

### Memory分段存储（Chunk-based）
**为什么必须分段**：
- 向量检索基于片段才能获得高相关性，整段文档粒度太粗
- Prompt预算有限，无法一次性塞入所有memory
- Conversation Summary是不断追加而非覆盖，每次总结都是新的一段

**Conversation Summary分段结构**：
```json
conversation_summary = [
    {id:1, text:"关于YOLO训练的问题总结..."},
    {id:2, text:"关于对话系统存储架构的讨论总结..."},
    {id:3, text:"用户简历修改需求总结..."}
]
```
每段独立生成embedding，按需检索top-K

**Long-term Memory分段结构**：
```json
{
  "user_preferences": [
      {id:101, text:"用户喜欢简洁类prompt"},
      {id:102, text:"用户经常做视频分析模型"}
  ],
  "task_history": [
      {id:201, text:"10月任务：构建对话系统的意图识别模块"},
      {id:202, text:"11月任务：设计记忆架构"}
  ]
}
```
每条事实/偏好/任务独立存储，方便检索、更新、删除

### Conversation Summary生成时的输入内容
**触发条件**：recent_messages≥5轮 或 token≥1200

**输入结构**（只提供增量内容）：
```json
{
  "recent_messages": [
      {"role":"user", "content":"..."},
      {"role":"assistant", "content":"..."}
  ],
  "intent": "对话系统架构咨询",
  "topic": "Memory & Vector Store",
  "last_summary": "之前总结到用户正在构建多阶段意图识别系统...",
  "summary_guideline": "请总结新内容，不要重复旧conversation_summary"
}
```

**关键原则**：
- ✅ 只传入recent_messages（未总结的新内容）
- ✅ 提供当前intent/topic（帮助模型理解上下文）
- ✅ 提供last_summary最后一段（避免重复总结）
- ❌ 不传入全历史对话
- ❌ 不传入全部conversation_summary
- ❌ 不传入long_term_memory

**输出**：生成新的conversation_summary_chunk，存储并生成embedding

### Memory更新机制与长度限制

#### Conversation Summary的更新与限制
**Conversation Summary不会无限增长，有以下限制策略**：

**方式A：保留最近N个chunk**
- 最多保留最近30个conversation_summary chunk
- 超过的旧chunk归档至冷存储或删除
- 原因：旧conversation_summary的embedding召回概率逐渐降低

**方式B：按相似主题合并**
- 若与上一段conversation_summary同主题 → 合并
- 若新主题 → 新增一个chunk
- 通过智能合并限制数量

**方式C：按token大小限制**
- conversation_summary总token不超过20k
- 超过就自动合并/裁剪出最重要的部分

**Conversation Summary召回机制**：
- ❌ 不会每次都全部召回
- ✅ 基于向量检索召回top-K
- 流程：`用户输入 → embedding → 向量检索conversation_summary_index → 找top-K → 拼给LLM`
- 越新的conversation_summary chunk越容易被召回（embedding相似度更高）
- 形成自然的"滑动窗口效应"

#### Long-term Memory的更新与限制
**必须严格结构化分段，有以下限制机制**：

**方式A：固定最大条数（最常见）**
- 用户偏好：最多存50条
- 用户长期事实：最多存100条
- 任务历史：最多存最近20条
- 超过就淘汰最不重要或最老的

**方式B：按重要性评分保留（高级系统）**
- LLM输出每条记忆的重要性分：0.0-1.0
- Memory Manager做weighted retention：
  - 重要性低、很久没被检索过 → 删除
  - 重要性高 → 永久保留
- OpenAI ReAct + Memory插件常用方法

**方式C：按主题聚合**
- 同类信息自动归并，减少冗余

**Long-term Memory召回机制**：
- ✅ 每次用户输入都会做向量检索
- ✅ 只返回top-K最相关的条目
- ✅ 向量库检索非常快（毫秒级）
- 流程：`用户query → embedding → 向量库检索 → top-K最相关 → 拼给LLM`

#### 完整记忆更新流程
```
用户输入
  ↓
写入短期记忆 recent_messages
  ↓
【召回阶段1】系统加载top-K conversation_summary（固定召回）
  ↓
【召回阶段2】系统加载long-term memory（向量检索，按需召回）
  ↓
把这些内容与用户消息一起打包成模型输入
  ↓
【生成阶段】模型生成reply
  ↓
判断是否触发conversation_summary更新
  - 若recent_messages超过阈值 → 触发总结
  ↓
conversation_summary模型生成新的conversation_summary_chunk
  ↓
写入conversation_summary_store
  ↓
生成embedding写入向量库(conversation_summary_index)
  ↓
清空recent_messages

【Long-term Memory更新】
任务结束/意图切换/确认新重要信息
  ↓
long-term memory writer向LLM提问：
"这段recent_messages有哪些值得写入长期记忆？"
  ↓
若LLM认为重要 → 生成long-term memory chunk
  ↓
写入long_term_memory_store
  ↓
写入向量库(long_term_index)
```

**关键顺序说明**：
- ✅ 先召回（conversation_summary + long-term memory），再生成reply
- ✅ Reply生成后，才判断是否需要更新conversation_summary
- ✅ Conversation Summary & memory是生成过程的输入语境，不是生成过程的一部分

#### Conversation Summary vs Long-term Memory对比
| 特性 | Conversation Summary | Long-term Memory |
|------|---------------------|------------------|
| 用途 | 维持上下文连贯（短期） | 保留长期事实、偏好（长期） |
| 存储方式 | chunk，偏向最近的 | chunk，按事实存 |
| 加载方式 | RAG（但新conversation_summary更相关） | RAG（纯召回模式） |
| 自动保留最近？ | ✅ 是（embedding相似度自然效果） | ❌ 否（完全看相关性） |
| 自动失效 | ✅ 被动淘汰 | ✅ 基于重要性或LRU |
| 调用频率 | 每轮对话检索top-K | 每轮对话检索top-K |

**关键理解**：
- Conversation Summary的"自动保留最近"是embedding相似度带来的，不是系统规则
- Conversation Summary会逐渐"滑向最近"的短期记忆（随对话走）
- Long-term Memory是需要时才被检索出来的知识（纯RAG模式，与时间无关）

## 三、两阶段召回机制与Prompt生成

### 多阶段检索（Multi-stage Retrieval）
用户每发一次消息，系统会经历两个召回阶段：

```
User Query
  ↓
【阶段1】Conversation Summary召回（固定召回）
  ↓
【阶段2】Long-term Memory检索（向量检索，按需召回）
  ↓
把内容合并 → Prompt输入模型
  ↓
模型生成回复（reply）
```

**关键顺序**：✅ 一定是先召回，再生成回复（reply）

#### 阶段1：Conversation Summary召回（必然发生）
**特点**：
- ✅ 总会发生，不论有没有长期记忆命中
- ✅ 让模型知道"当前对话刚刚发生了什么"
- ✅ 窗口化，会随着对话发展自动更新
- ✅ 类似滑动窗口，只保留"当下有用的短期记忆"

**作用**：维持对话连续性，保留最近相关内容

#### 阶段2：Long-term Memory召回（有条件发生）
**特点**：
- ❌ 不一定每次都触发
- ✅ 取决于用户当前输入是否与记忆库中的内容向量相似
- ✅ 基于向量检索（vector search）：query embedding → 相似度检索 → top-K召回

**示例**：
- "我们上次讲过包裹识别逻辑" → ✅ 会触发长期记忆召回
- "今天天气怎么样" → ❌ 不会召回长期记忆

#### 两阶段对比
| 特性 | Conversation Summary召回 | Long-term Memory召回 |
|------|------------------------|---------------------|
| 是否必然发生 | ✅ 是 | ❌ 按需 |
| 召回方式 | 自动包含最近的 | 向量相似度检索 |
| 作用 | 短期上下文理解 | 长期知识关联 |
| 内容 | "你们刚刚聊什么" | "你们过去几周/几月聊过什么" |

**为什么必须两个阶段**：
- Conversation Summary：帮助模型理解当前对话上下文
- Long-term Memory：帮助模型关联历史知识和偏好
- 两者缺一不可

### 完整召回与生成流程
```
用户消息输入
  ↓
【召回阶段1】系统加载top-K conversation_summary（固定）
  ↓
【召回阶段2】系统加载long-term memory（向量检索命中部分）
  ↓
把这些内容与用户消息一起打包成模型输入
  ↓
【生成阶段】模型生成reply
```

**关键理解**：
- ✅ 召回是前置阶段，生成是后置阶段
- ✅ 模型生成回复时必须已经看到conversation_summary和long-term memory
- ✅ Conversation Summary & memory不是生成过程的一部分，而是生成过程的输入语境

### 真实LLM Prompt构成
```
[
  System Prompt
    ↓
  Conversation Summary（top-K）
    ↓
  Retrieved Long-term Memory（top-K）
    ↓
  Recent conversation turns（最近几轮）
    ↓
  User当前问题
]
  ↓
输入模型 → 生成回复
```

### Prompt内容筛选策略
每次调用LLM时，不直接传入整个JSON，而是筛选：
- 最近几轮消息（recent_messages）
- 当前意图和话题（intent/topic）
- 与当前消息最相关的conversation_summary片段（top-K）
- 与当前消息最相关的long_term_memory片段（top-K）

### 向量生成与存储时机
**什么时候生成向量**：
- **Conversation Summary**：生成conversation_summary的那一刻（同步或异步）生成embedding并写入向量库
- **Long-term Memory**：触发更新时（任务结束/意图切换）生成embedding并写入
- **联网检索结果**：默认不生成向量、不存储（临时内容，用完即丢弃）

**是否一定需要向量**：
- **不需要**：conversation_summary很少、内容很短、系统小规模、只用规则匹配
- **需要**：conversation_summary很多、长期使用、大量检索结果需要二次筛选、需要语义相关性检索

**信息类型存储策略**：
| 信息类型 | 是否存入long_term_memory | 是否生成向量 |
|---------|------------------------|------------|
| conversation_summary | 存 | 存向量 |
| long_term_memory（用户偏好/持久信息） | 存 | 存向量 |
| 联网检索结果（临时知识） | ❌不存 | ❌不存向量 |
| 高价值检索结果（需要持久化） | 可选 | 可选 |

### 向量检索流程
1. 将conversation_summary/long_term_memory按片段切分并生成embedding
2. 用户最新消息生成embedding
3. 通过余弦相似度排序，选取top-K最相关片段
4. 作为prompt上下文拼接给LLM

### 存储与检索架构
- **向量数据库**：保留ID和向量，用于快速检索top-K相关片段
- **JSON/文本存储**：保存完整内容
- **生成prompt时**：通过检索ID获取对应JSON/text片段，拼接给LLM
- 既保证信息完整性，又能高效检索和控制token

**典型文件结构**：
```
memory_store/
  conversation_summary/
    summary_001.json
    summary_002.json
  long_term_memory/
    pref_001.json
    task_001.json
  vector_index/
    summary_001.vec
    pref_001.vec
```

## 四、联网检索优化

### 情况A：绝大多数实际系统（90%）- 不存向量
**流程**：
```
用户问题 → 搜索引擎API返回几百条结果 → Rerank/LLM过滤top-K → 拼接给LLM生成答案 → 丢弃
```

**为什么不存**：
- 联网检索结果是临时的、一次性的，不是系统长期知识
- 下次用户可能不需要，存储成本高
- 会污染长期知识库
- 这被称为"ephemeral context（短暂上下文）"

### 情况B：知识增强聊天（高级玩法）- 选择性缓存
**适用场景**：自建知识库机器人

**流程**：
```
检索得到内容 → LLM判断重要性 → 若值得长期保存 → 写入long_term_memory → 生成向量写入向量库
```

这被称为"RAG Memory Augmentation"，属于高复杂度系统

### 处理大量检索结果
即使检索返回几百条结果，也不会全部给LLM：
1. 对已知内容预生成embedding并存储向量数据库
2. 用户query生成embedding，在向量空间召回top-K相关片段
3. 仅将top-K文本片段拼接给LLM生成回复

### 实时性优化
- **预生成策略**：对已知内容预生成embedding并存储
- **查询时**：直接top-K召回相关片段
- **新内容**：异步生成embedding并加入数据库
- 保证对话实时性，同时逐步纳入新知识

## 总结
这是一套成熟的对话系统架构设计，核心是**分层记忆+向量检索+异步处理**，在保证对话连续性的同时控制延迟和成本。参考了OpenAI、Anthropic等对话式LLM系统的标准架构。
