# 对话系统上下文管理项目

基于多层记忆架构的智能对话系统，支持短期记忆、长期记忆和向量检索。

## 项目架构

```
src/
├── domain/                      # 领域模型层
│   └── chat_session.py         # 会话数据模型（ChatSession, Message, Memory等）
│
├── core/                        # 核心业务逻辑层
│   ├── session_manager.py      # 会话管理器（CRUD、状态更新）
│   ├── base.py                 # 基础类
│   ├── service.py              # 服务基类
│   └── exception.py            # 异常定义
│
├── application/                 # 应用服务层
│   └── memory_manager.py       # 记忆管理器（协调总结生成和检索）
│
├── infrastructure/              # 基础设施层
│   ├── service/
│   │   ├── llm/                # LLM 服务
│   │   ├── summary_service.py  # 总结生成服务
│   │   └── vector_store.py     # 向量存储服务
│   └── handler/                # 处理器
│
├── utils/                       # 工具函数
│   └── function.py
│
├── config.yaml                  # 配置文件
└── main.py                      # 入口文件
```

## 核心组件

### 1. Domain Layer (领域模型层)

**chat_session.py**
- `Message`: 消息模型
- `ConversationSummary`: 对话总结模型
- `ShortTermMemory`: 短期记忆模型
- `LongTermMemory`: 长期记忆模型
- `ChatSession`: 会话状态模型

### 2. Core Layer (核心业务逻辑层)

**SessionManager** - 会话管理器
- `create_session()`: 创建新会话
- `load_session()`: 加载会话
- `save_session()`: 保存会话
- `add_message()`: 添加消息到短期记忆
- `update_intent()`: 更新意图
- `update_topic()`: 更新话题
- `update_preference()`: 更新用户偏好
- `should_trigger_summary()`: 判断是否需要触发总结

### 3. Application Layer (应用服务层)

**MemoryManager** - 记忆管理器

**Conversation Summary 管理：**
- `generate_summary()`: 生成对话总结
  - 检查是否需要总结
  - 调用 LLM 生成 summary
  - 添加到 conversation_summary
  - 生成并存储 embedding
  - 清空 recent_messages

- `retrieve_summaries()`: 召回相关总结
  - 向量检索 top-K conversation_summary

**Long-term Memory 管理：**
- `add_long_term_memory()`: 添加长期记忆
  - 添加新记忆到 long_term_memory
  - 生成并存储 embedding

- `retrieve_long_term_memory()`: 召回相关长期记忆
  - 向量检索 top-K long_term_memory

### 4. Infrastructure Layer (基础设施层)

**SummaryService** - 总结生成服务
- 调用 LLM 生成对话总结
- 处理 prompt 构建和结果解析

**VectorStoreService** - 向量存储服务
- 生成文本 embedding
- 存储和检索向量
- Top-K 相似度搜索

## 核心流程

### 对话处理流程

```
用户输入
  ↓
SessionManager.add_message()  # 添加消息到短期记忆
  ↓
MemoryManager.retrieve_summaries()  # 召回相关总结
  ↓
MemoryManager.retrieve_long_term_memory()  # 召回长期记忆
  ↓
构建 Prompt（recent_messages + summaries + long_term_memory）
  ↓
调用 LLM 生成回复
  ↓
SessionManager.should_trigger_summary()  # 判断是否需要总结
  ↓
MemoryManager.generate_summary()  # 生成总结（如果需要）
```

### 记忆管理策略

**短期记忆（Short-term Memory）：**
- `recent_messages`: 最近几轮对话
- `conversation_summary`: 对话总结 chunks
- 触发条件：消息数 ≥ 5 或 token ≥ 1200
- 总结后清空 recent_messages

**长期记忆（Long-term Memory）：**
- 存储用户偏好、历史任务、重要事实
- 触发条件：意图切换、话题切换
- 通过 LLM 提取重要信息

**向量检索：**
- Conversation Summary 和 Long-term Memory 都生成 embedding
- 基于向量相似度检索 top-K 相关内容
- 用于构建 LLM prompt 的上下文

## 设计原则

1. **分层架构**：清晰的职责分离
   - Domain: 数据模型
   - Core: 纯业务逻辑
   - Application: 服务协调
   - Infrastructure: 外部依赖

2. **依赖方向**：单向依赖，从外向内
   - Application → Core → Domain
   - Infrastructure → Domain

3. **异步处理**：总结生成不阻塞主流程

4. **向量检索**：基于 embedding 的语义检索

## 配置说明

配置文件位于 `src/config.yaml`，包含：
- 环境配置（dev/test/prod）
- LLM 模型配置
- 向量数据库配置
- 阈值配置（消息数、token 数等）

## 文档

详细的架构设计文档请参考：
- [Context_Management.MD](docs/Context_Management.MD) - 上下文管理架构详细说明

## 开发状态

当前处于架构设计阶段，核心组件的接口已定义，具体实现待完成。

## 下一步计划

1. 实现 SessionManager 的基础功能
2. 实现 SummaryService（LLM 调用）
3. 实现 VectorStoreService（向量存储）
4. 实现 MemoryManager 的完整流程
5. 添加配置管理
6. 添加测试用例
