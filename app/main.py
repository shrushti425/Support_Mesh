import logging
from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routes import tickets, dashboard

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("supportmesh.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform database initialization on startup
    logger.info("Initializing database on startup...")
    await init_db()
    logger.info("Database initialization complete.")
    yield
    logger.info("Shutting down SupportMesh application...")

app = FastAPI(
    title="SupportMesh Operations Hub",
    description="AI-powered Customer Support Integration Agent with RAG and Vector Search",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin testing/webhooks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickets.router)
app.include_router(dashboard.router)

@app.get("/", status_code=status.HTTP_307_TEMPORARY_REDIRECT, tags=["Root"])
async def root_redirect():
    # Redirect root visitors straight to the dashboard for seamless UX
    return RedirectResponse(url="/dashboard")
