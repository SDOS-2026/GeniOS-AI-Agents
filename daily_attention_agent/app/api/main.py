import logging
from fastapi import FastAPI

from daily_attention_agent.app.services.mcp_client import lifespan
from daily_attention_agent.app.api.routers import agent

# Set up simple logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Daily Attention Agent",
    description="Backend service for prioritizing daily focus using MCP.",
    lifespan=lifespan
)

# Include the agent routes
app.include_router(agent.router)

@app.get("/")
def read_root():
    return {"message": "Daily Attention Agent service is running. POST to /run to execute."}
