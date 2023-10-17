# Standard Library
import os
import uuid
from datetime import datetime
from typing import List, Optional

# Third-party Libraries
from databases import Database
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, UUID4
from sqlalchemy import (CheckConstraint, Column, DateTime, Float, ForeignKey, MetaData, Text, create_engine, String)
from sqlalchemy.dialects.postgresql import UUID, ENUM  
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Environment setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
API_TOKEN = os.getenv("API_TOKEN")
security = HTTPBearer()
database = Database(DATABASE_URL)
metadata = MetaData()

# Enum Type for Sender
SenderTypeEnum = ENUM('User', 'Bot', name='sender_type_enum')

Base = declarative_base(metadata=metadata)

class Message(Base):
    __tablename__ = "message"
    message_id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.conversation_id"), nullable=False)
    sender_type = Column(SenderTypeEnum, nullable=True)
    content = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=True)
    sentiment_score = Column(Float, CheckConstraint("sentiment_score BETWEEN -1 AND 1"), nullable=True)
    intent_label = Column(String(255), nullable=True)
    intent_confidence_score = Column(Float, CheckConstraint("intent_confidence_score BETWEEN 0 AND 1"), nullable=True)

class MessageList(BaseModel):
    conversation_id: UUID4
    sender_type: Optional[str]
    content: Optional[str]
    timestamp: Optional[datetime]
    sentiment_score: Optional[float]
    intent_label: Optional[str]
    intent_confidence_score: Optional[float]

class MessageCreate(BaseModel):
    conversation_id: UUID4
    sender_type: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[datetime] = datetime.utcnow()
    sentiment_score: Optional[float] = None
    intent_label: Optional[str] = None
    intent_confidence_score: Optional[float] = None

class MessageResponse(MessageCreate):
    message_id: UUID4

message_app = FastAPI()

def verify_token(authorization: HTTPAuthorizationCredentials = Depends(security)):
    static_token = API_TOKEN
    if authorization.credentials != static_token:
        raise HTTPException(status_code=401, detail="Invalid token or unauthorized!")
    return authorization.credentials

@message_app.on_event("startup")
async def startup_event():
    await database.connect()

@message_app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()

@message_app.post("/message/", response_model=MessageResponse)
async def create_message(message: MessageCreate, token: str = Depends(verify_token)):
    new_message = message.dict()
    if new_message["sentiment_score"] is None:
        del new_message["sentiment_score"]
    new_message["message_id"] = str(uuid.uuid4())
    result = await database.execute(Message.__table__.insert().values(new_message))
    
    # Return the full message data including the new message_id
    return {**new_message, "message_id": new_message["message_id"]}

@message_app.get("/message/conversation/{conversation_id}", response_model=List[MessageList])
async def get_messages_for_conversation(conversation_id: UUID4, token: str = Depends(verify_token)):
    query = Message.__table__.select().where(Message.conversation_id == conversation_id)
    messages = await database.fetch_all(query)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this conversation")
    return messages

@message_app.get("/message/hello/")
def hello_world(token: str = Depends(verify_token)):
    return {"message": "Hello, World!"}

@message_app.put("/message/{message_id}", response_model=MessageResponse)
async def update_message(message_id: UUID4, update_data: MessageCreate, token: str = Depends(verify_token)):
    update_values = {key: value for key, value in update_data.dict().items() if value is not None}
    query = (
        Message.__table__.update()
        .where(Message.message_id == message_id)
        .values(update_values)
        .returning(Message)
    )
    result = await database.fetch_one(query)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(message_app, host="0.0.0.0", port=8001)
