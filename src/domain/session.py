"""
Session State Management Module

This module defines the core data structures for chat sessions, including messages, memory, and session state.
Used to manage conversation history and context information between users and AI assistants.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Message(BaseModel):
    """
    Message Model
    
    Represents a single message in a conversation, containing role and content information.
    """
    role: str = Field(..., description="Role of the message sender, e.g., 'user' or 'assistant'")
    content: str = Field(..., description="The actual text content of the message")


class ConversationSummary(BaseModel):
    """
    Conversation Summary Model
    
    Stores summary information of conversations for compressing and preserving key content from historical dialogues.
    """
    timestamp: int = Field(..., description="Timestamp when the summary was generated (Unix timestamp in seconds)")
    content: str = Field(..., description="Text content of the conversation summary")


class ShortTermMemory(BaseModel):
    """
    Short-Term Memory Model
    
    Stores recent messages and conversation summaries from the current session to maintain immediate context.
    """
    recent_messages: List[Message] = Field(..., description="List of recent messages in chronological order")
    conversation_summary: List[ConversationSummary] = Field(..., description="List of conversation summaries for the current session")


class LongTermMemory(BaseModel):
    """
    Long-Term Memory Model
    
    Stores summary information from historical sessions for cross-session context retention and knowledge accumulation.
    """
    timestamp: int = Field(..., description="Timestamp when the memory was created (Unix timestamp in seconds)")
    summaries: List[ConversationSummary] = Field(..., description="List of historical conversation summaries")


class ChatState(BaseModel):
    """
    Chat Session State Model
    
    Represents the complete chat session state, including session identifier, memory, intent, topic, and other information.
    This is the core data structure for session management.
    """
    session_id: str = Field(..., description="Unique identifier for the session")
    short_term_memory: ShortTermMemory = Field(..., description="Short-term memory storing recent messages and summaries from the current session")
    long_term_memory: List[LongTermMemory] = Field(..., description="List of long-term memories storing summary information from historical sessions")
    intent: str = Field(..., description="Current intent or purpose of the user")
    topic: str = Field(..., description="Current topic of the conversation")
    preference: dict = Field(..., description="Dictionary of user preference settings for personalized configuration")
    last_user_message: str = Field(..., description="Content of the last message sent by the user")
    update_time: int = Field(..., description="Timestamp of the last session update (Unix timestamp in seconds)")
