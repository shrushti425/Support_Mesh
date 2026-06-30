import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    account_tier = Column(String(50), nullable=False, default="free")  # e.g., free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    tickets = relationship("Ticket", back_populates="customer", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(50), nullable=False, default="medium")  # e.g., low, medium, high, urgent
    status = Column(String(50), nullable=False, default="open")  # open, pending, resolved
    classification = Column(String(100), nullable=True)  # e.g., billing, refunds, etc.
    draft_response = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    latency = Column(Float, nullable=True)  # Latency in seconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    customer = relationship("Customer", back_populates="tickets")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)  # billing, refunds, VPN troubleshooting, etc.
    embedding = Column(Vector(384), nullable=False)  # 384 dimensions matching all-MiniLM-L6-v2
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
