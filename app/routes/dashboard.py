import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Ticket, Customer
from app.schemas import StatsResponse

logger = logging.getLogger("supportmesh.routes.dashboard")
router = APIRouter()

# Mount templates directory
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    try:
        # 1. Total count
        total_stmt = select(func.count(Ticket.id))
        total_res = await db.execute(total_stmt)
        total_tickets = total_res.scalar() or 0

        # 2. Resolved count
        resolved_stmt = select(func.count(Ticket.id)).where(Ticket.status == "resolved")
        resolved_res = await db.execute(resolved_stmt)
        resolved_tickets = resolved_res.scalar() or 0

        # 3. Resolution rate (percentage)
        resolution_rate = round((resolved_tickets / total_tickets * 100), 2) if total_tickets > 0 else 0.0

        # 4. Average latency
        avg_latency_stmt = select(func.avg(Ticket.latency))
        avg_latency_res = await db.execute(avg_latency_stmt)
        avg_latency = round(avg_latency_res.scalar() or 0.0, 3)

        # 5. Category breakdown
        category_stmt = select(Ticket.classification, func.count(Ticket.id)).group_by(Ticket.classification)
        category_res = await db.execute(category_stmt)
        category_breakdown = {row[0] or "general support": row[1] for row in category_res.all()}

        # 6. Recent tickets (last 10)
        recent_stmt = (
            select(Ticket)
            .options(joinedload(Ticket.customer))
            .order_by(Ticket.created_at.desc())
            .limit(10)
        )
        recent_res = await db.execute(recent_stmt)
        recent_tickets = list(recent_res.scalars().all())

        # 7. Customers (to populate dropdown on the UI dashboard)
        customers_stmt = select(Customer).order_by(Customer.name.asc())
        customers_res = await db.execute(customers_stmt)
        customers_list = list(customers_res.scalars().all())

        return {
            "total_tickets": total_tickets,
            "resolution_rate": resolution_rate,
            "avg_latency": avg_latency,
            "category_breakdown": category_breakdown,
            "recent_tickets": recent_tickets,
            "customers": customers_list
        }
    except Exception as e:
        logger.error(f"Error computing dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving stats")
