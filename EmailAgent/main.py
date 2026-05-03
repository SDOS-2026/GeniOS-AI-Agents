"""
GeniOS EmailAgent — FastAPI service (Port 8002).

Exposes /run, /resume, /state, /health endpoints for the
email agent LangGraph workflow with interrupt/resume support.
"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything else

from fastapi import FastAPI
from routers.email import router
from app.graph.graph import initialise_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from app.mcp_client import initialize_mcp_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise graph + checkpointer. Shutdown: cleanup."""
    logger.info("[EmailAgent] Starting up...")
    initialize_mcp_client()
    await initialise_graph()
    logger.info("[EmailAgent] Service ready.")
    yield
    logger.info("[EmailAgent] Shutting down.")


app = FastAPI(
    title="GeniOS EmailAgent",
    description="Email drafting, inbox review, and reply agent with human-in-the-loop interrupts.",
    lifespan=lifespan,
)

app.include_router(router)
