from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, String, Float, ForeignKey, MetaData, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import databases
import os
from dotenv import load_dotenv
from pydantic import BaseModel, UUID4  # Use UUID4 from pydantic
import uuid
from datetime import datetime
from uuid import UUID as UUIDType  # Adding the Python's UUID type for clarity
from typing import Optional
from typing import List
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)
metadata = MetaData()
API_TOKEN = os.getenv("API_TOKEN")
security = HTTPBearer()

def verify_token(authorization: HTTPAuthorizationCredentials = Depends(security)):
    static_token = API_TOKEN
    if authorization.credentials != static_token:
        raise HTTPException(status_code=401, detail="Invalid token or unauthorized!")
    return authorization.credentials

# Enum Type for Conversation Status
ConversationStatus = ENUM('ongoing', 'terminated', name='conversation_status')
Base = declarative_base(metadata=metadata)

class Conversation(Base):
    __tablename__ = "conversation"
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('company.company_id'))
    bot_version = Column(String(50), nullable=False)  # Limiting to 50 characters as per SQL definition
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(ConversationStatus, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    intent_label = Column(String(255))
    intent_confidence_score = Column(Float)

class ConversationIDResponse(BaseModel):
    conversation_id: UUID4

class ConversationCreate(BaseModel):
    company_id: Optional[str] = None
    bot_version: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    sentiment_score: Optional[float] = None
    intent_label: Optional[str] = None
    intent_confidence_score: Optional[float] = None

class ConversationResponse(ConversationCreate):
    conversation_id: UUID4
    company_id: UUID4

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@app.on_event("startup")
async def startup_event():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()

@app.post("/conversation/", response_model=ConversationIDResponse)
async def create_conversation(conversation: ConversationCreate, token: str = Depends(verify_token)):
    async with database.transaction():
        new_conversation = conversation.dict()
        new_conversation["conversation_id"] = str(uuid.uuid4())
        new_conversation["start_time"] = datetime.utcnow()
        result = await database.execute(Conversation.__table__.insert().values(new_conversation))
    return {"conversation_id": new_conversation["conversation_id"]}

@app.get("/conversation/", response_model=List[ConversationResponse])
async def list_conversations(token: str = Depends(verify_token)):
    query = Conversation.__table__.select()
    conversations = await database.fetch_all(query)
    return conversations

@app.delete("/conversation/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUIDType, token: str = Depends(verify_token)):
    async with database.transaction():
        query = (
            Conversation.__table__.delete()
            .where(Conversation.conversation_id == conversation_id)
        )
        result = await database.execute(query)
        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")
    return {}

@app.put("/conversation/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: UUIDType, update_data: ConversationCreate, token: str = Depends(verify_token)):
    async with database.transaction():
        update_values = {key: value for key, value in update_data.dict().items() if value is not None}
        query = (
            Conversation.__table__.update()
            .where(Conversation.conversation_id == conversation_id)
            .values(update_values)
            .returning(Conversation)
        )
        result = await database.fetch_one(query)
        if result is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    return result

@app.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def read_conversation(conversation_id: UUIDType, token: str = Depends(verify_token)):
    query = Conversation.__table__.select().where(Conversation.conversation_id == conversation_id)
    conversation = await database.fetch_one(query)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
