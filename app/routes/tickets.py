import time
import logging
import asyncio
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Customer, Ticket, KnowledgeBase
from app.schemas import TicketCreate, TicketResponse, StatsResponse
from app.services.rag import rag_service
from app.services.llm import llm_service
from app.services.webhook import webhook_service

logger = logging.getLogger("supportmesh.routes.tickets")
router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_in: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    start_time = time.perf_counter()
    logger.info(f"Received support ticket for customer ID: {ticket_in.customer_id}")

    try:
        # 1. Fetch customer details from PostgreSQL
        customer_stmt = select(Customer).where(Customer.id == ticket_in.customer_id)
        customer_res = await db.execute(customer_stmt)
        customer = customer_res.scalar_one_or_none()

        # 2. Handle missing customer (404)
        if not customer:
            logger.warning(f"Customer with ID {ticket_in.customer_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {ticket_in.customer_id} not found"
            )

        # 3. Fetch customer's recent ticket history (last 5 tickets)
        history_stmt = (
            select(Ticket)
            .where(Ticket.customer_id == customer.id)
            .order_by(Ticket.created_at.desc())
            .limit(5)
        )
        history_res = await db.execute(history_stmt)
        history_tickets = history_res.scalars().all()
        history_list = [
            {
                "subject": t.subject,
                "body": t.body,
                "draft_response": t.draft_response,
                "status": t.status
            }
            for t in history_tickets
        ]

        # 4. Generate embedding and search knowledge base using pgvector (top 3 articles)
        relevant_articles = await rag_service.search_knowledge_base(
            db, query=f"{ticket_in.subject} {ticket_in.body}", limit=3
        )
        articles_list = [
            {
                "title": art.title,
                "category": art.category,
                "content": art.content
            }
            for art in relevant_articles
        ]

        # 5. Send context to Groq LLM (OpenAI SDK + tool calling)
        analysis = await llm_service.analyze_ticket(
            customer_name=customer.name,
            customer_tier=customer.account_tier,
            history=history_list,
            articles=articles_list,
            subject=ticket_in.subject,
            body=ticket_in.body
        )

        # Compute Processing Latency
        latency = round(time.perf_counter() - start_time, 3)

        # 6. Save the ticket result in PostgreSQL
        new_ticket = Ticket(
            customer_id=customer.id,
            subject=ticket_in.subject,
            body=ticket_in.body,
            priority=ticket_in.priority,
            status=analysis.get("status", "open"),
            classification=analysis.get("classification", "general support"),
            draft_response=analysis.get("draft_response"),
            confidence_score=analysis.get("confidence_score", 0.0),
            latency=latency
        )
        db.add(new_ticket)
        await db.commit()
        await db.refresh(new_ticket)

        # Bind customer explicitly for serialization mapping
        new_ticket.customer = customer

        # 7. Prepare webhook payload
        webhook_payload = {
            "event": "ticket.created",
            "ticket": {
                "id": str(new_ticket.id),
                "subject": new_ticket.subject,
                "body": new_ticket.body,
                "priority": new_ticket.priority,
                "status": new_ticket.status,
                "classification": new_ticket.classification,
                "draft_response": new_ticket.draft_response,
                "confidence_score": new_ticket.confidence_score,
                "latency": new_ticket.latency,
                "created_at": new_ticket.created_at.isoformat(),
            },
            "customer": {
                "id": str(customer.id),
                "name": customer.name,
                "email": customer.email,
                "account_tier": customer.account_tier
            }
        }

        # 8. Fire webhook asynchronously using background task (using httpx)
        background_tasks.add_task(webhook_service.trigger_webhook, webhook_payload)

        # 9. Return the full ticket response
        return new_ticket

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions (e.g. 404) directly
        raise
    except Exception as e:
        logger.error(f"Internal error processing support ticket: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing the support ticket."
        )

@router.get("", response_model=List[TicketResponse])
async def get_tickets(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Ticket)
        .options(joinedload(Ticket.customer))
        .order_by(Ticket.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Ticket)
        .options(joinedload(Ticket.customer))
        .where(Ticket.id == ticket_id)
    )
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

# Demo Webhook Receiver Endpoint
# This allows the webhook to succeed locally inside the container
@router.post("/webhook-demo-endpoint", status_code=status.HTTP_200_OK)
async def webhook_demo_endpoint(payload: Dict[str, Any]):
    logger.info(f"DEMO WEBHOOK RECEIVED PAYLOAD: {payload}")
    return {"message": "Webhook processed successfully", "status": "received"}
