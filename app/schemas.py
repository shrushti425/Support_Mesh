from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict

# Customer Schemas
class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    account_tier: str = Field("free", max_length=50)

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Ticket Schemas
class TicketCreate(BaseModel):
    customer_id: UUID
    subject: str = Field(..., max_length=255)
    body: str
    priority: str = Field("medium", max_length=50)

class TicketResponse(BaseModel):
    id: UUID
    customer_id: UUID
    subject: str
    body: str
    priority: str
    status: str
    classification: Optional[str] = None
    draft_response: Optional[str] = None
    confidence_score: Optional[float] = None
    latency: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True

# KnowledgeBase Schemas
class KnowledgeBaseCreate(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    category: str = Field(..., max_length=100)

class KnowledgeBaseResponse(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True

# Dashboard Stat Schemas
class StatsResponse(BaseModel):
    total_tickets: int
    resolution_rate: float
    avg_latency: float
    category_breakdown: Dict[str, int]
    recent_tickets: List[TicketResponse]
    customers: List[CustomerResponse]
