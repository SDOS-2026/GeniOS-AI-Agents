import logging
import uuid

from fastapi import APIRouter, HTTPException
from langgraph.types import Command

from schemas import RunRequest, RunResponse, ResumeRequest, ResumeResponse
from app.graph.graph import get_compiled_graph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])


def _extract_interrupt(events: list) -> dict | None:
    """Pull the interrupt payload out of a stream event list."""
    for event in events:
        if "__interrupt__" in event:
            interrupts = event["__interrupt__"]
            if interrupts:
                return interrupts[0].value
    return None


@router.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    """Start a new email agent run from a user prompt."""
    graph = get_compiled_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    logger.info(f"[EmailAgent] Starting run thread_id={thread_id} prompt={req.prompt!r}")

    try:
        events = []
        async for event in graph.astream(
            {"user_prompt": req.prompt},
            config=config,
            stream_mode="updates",
        ):
            events.append(event)
            if "__interrupt__" in event:
                break

        interrupt_payload = _extract_interrupt(events)
        if interrupt_payload:
            return RunResponse(
                thread_id=thread_id,
                status="interrupted",
                interrupt_payload=interrupt_payload,
            )

        # Graph ran to END without interrupting
        return RunResponse(
            thread_id=thread_id,
            status="done",
            interrupt_payload=None,
        )

    except Exception as e:
        logger.exception(f"[EmailAgent] Run failed: {e}")
        return RunResponse(
            thread_id=thread_id,
            status="error",
            interrupt_payload={"error": str(e)},
        )


@router.post("/resume", response_model=ResumeResponse)
async def resume(req: ResumeRequest):
    """Resume an interrupted run with a user response."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": req.thread_id}}

    # Verify thread exists
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")

    logger.info(f"[EmailAgent] Resuming thread_id={req.thread_id} response={req.response}")

    try:
        events = []
        async for event in graph.astream(
            Command(resume=req.response),
            config=config,
            stream_mode="updates",
        ):
            events.append(event)
            if "__interrupt__" in event:
                break

        interrupt_payload = _extract_interrupt(events)
        if interrupt_payload:
            return ResumeResponse(
                thread_id=req.thread_id,
                status="interrupted",
                interrupt_payload=interrupt_payload,
            )

        final_state = await graph.aget_state(config)
        return ResumeResponse(
            thread_id=req.thread_id,
            status="done",
            result={"sent": final_state.values.get("sent")},
        )

    except Exception as e:
        logger.exception(f"[EmailAgent] Resume failed: {e}")
        return ResumeResponse(
            thread_id=req.thread_id,
            status="error",
            interrupt_payload={"error": str(e)},
        )


@router.get("/state/{thread_id}")
async def get_state(thread_id: str):
    """Returns the current persisted state — useful for reconnects."""
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Thread not found")
    return state.values


@router.get("/health")
async def health():
    """Service health check."""
    return {"service": "email", "status": "ok"}
