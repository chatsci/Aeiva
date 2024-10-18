from pydantic import BaseModel, Field
from typing import Any, Optional, Set, Dict
from uuid import uuid4
from datetime import datetime

class Message(BaseModel):
    # header fields
    id: str = Field(default_factory=lambda: uuid4().hex, description="Unique identifier for the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    sender_id: str = Field(..., description="Identifier of the sender")
    receiver_id: Optional[str] = Field(None, description="Identifier of the receiver; None for broadcast")
    protocol: str = Field(..., description="Communication protocol type (e.g., streaming, event, sync)")
    message_type: str = Field(..., description="Type of message (e.g., perception, action, event, command, response)")
    priority: str = Field(default="medium", description="Priority level of the message")
    
    # payload fields
    data_type: str = Field(..., description="Type of data contained (e.g., text, image, audio, video, signal)")
    content: Any = Field(..., description="Actual content or reference to the data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the message")
    
    # context fields
    conversation_id: Optional[str] = Field(None, description="Identifier linking related messages")
    agent_state: Optional[str] = Field(None, description="State information of the agent")
    
    class Config:
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2024-04-27T12:00:00Z",
                "sender_id": "sensor_01",
                "receiver_id": "brain_01",
                "protocol": "streaming",
                "message_type": "perception",
                "priority": "high",
                "data_type": "audio",
                "content": {"audio_data": "base64_encoded_audio"},
                "conversation_id": "convo_001",
                "agent_state": "active"
            }
        }