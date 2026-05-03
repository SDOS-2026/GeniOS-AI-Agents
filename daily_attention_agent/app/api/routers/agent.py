import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from daily_attention_agent.app.core.runner import run_daily_attention_agent
from daily_attention_agent.app.services.run_store import run_store
from daily_attention_agent.app.services.mcp_client import MCPConnectionManager

router = APIRouter()

class RunRequest(BaseModel):
    user_id: str
    workspace_id: str
    vip_senders: List[str] = []
    keywords: List[str] = []
    depth_mode: str = "quick"
    output_mode: str = "brief_only"


@router.post("/run")
async def run_agent(run_request: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    run_store[run_id] = {"status": "running", "result": None}

    # Explicit DI — no hidden framework coupling
    mcp_session = MCPConnectionManager.get_session()

    async def execute_and_store():
        try:
            print(f"[INFO] Starting agent run: {run_id}")
            result = await run_daily_attention_agent(
                payload=run_request.model_dump(),
                mcp_session=mcp_session,
            )
            run_store[run_id]["status"] = "success"
            
            # extract serializable parts for basic API response
            safe_result = {
                "attention_items": result.get("attention_items", []),
                "risks": result.get("risks", []),
                "opportunities": result.get("opportunities", []),
                "warnings": result.get("warnings", []),
                "run_completed_at": result.get("run_completed_at")
            }
            run_store[run_id]["result"] = safe_result
            print(f"[INFO] Agent run {run_id} completed successfully.")
        except Exception as e:
            import traceback
            error_msg = f"Error during agent execution: {str(e)}"
            print(f"[ERROR] Agent run {run_id} failed: {error_msg}")
            print(traceback.format_exc())
            run_store[run_id]["status"] = "error"
            run_store[run_id]["result"] = error_msg


    background_tasks.add_task(execute_and_store)
    return {"run_id": run_id, "status": "running"}


@router.get("/status/{run_id}")
async def get_status(run_id: str):
    if run_id not in run_store:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return run_store[run_id]

@router.get("/history")
async def get_history():
    return [{"run_id": k, "status": v["status"]} for k, v in run_store.items()]
