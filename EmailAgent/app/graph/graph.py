from langgraph.graph import StateGraph
from app.graph.state import EmailAgentState
from app.nodes.entry import entry_node
from app.nodes.classify import classify_node
from app.nodes.summarize import summarize_node
from app.nodes.extract import extract_node
from app.nodes.risk import risk_node
from app.nodes.approval import approval_node
from app.nodes.draft import draft_node
from app.nodes.compose import compose_node

from app.nodes.input_agent import input_agent_node
from app.nodes.fetch import fetch_node
from app.nodes.inbox_review import inbox_review_node
from app.nodes.review import review_node
from app.nodes.send import send_node
from app.memory.memory_write import memory_write_node
from app.memory.memory_retrieve import memory_retrieve_node

from langgraph.graph import END

def build_graph():
    graph = StateGraph(EmailAgentState)

    # Nodes
    graph.add_node("entry", entry_node)
    graph.add_node("input_agent", input_agent_node)
    graph.add_node("fetch", fetch_node)
    
    graph.add_node("classify", classify_node)
    graph.add_node("inbox_review", inbox_review_node)
    
    graph.add_node("summarize", summarize_node)
    graph.add_node("extract", extract_node)
    graph.add_node("risk", risk_node)
    graph.add_node("approval", approval_node)
    graph.add_node("draft", draft_node)
    graph.add_node("compose", compose_node)
    graph.add_node("review", review_node)
    graph.add_node("send", send_node)
    graph.add_node("memory_write", memory_write_node)
    graph.add_node("memory_retrieve", memory_retrieve_node)

    # Entry Point -> Input Agent (Router)
    graph.set_entry_point("input_agent")
    
    def memory_retrieve_router(state):
    # inbox reply path
        if state.get("mode") == "REPLY" or state.get("user_action") == "REPLY":
            return "draft"
        # compose path
        return "compose"
        
    # Router Logic
    graph.add_conditional_edges(
        "input_agent",
        lambda s: s.get("mode"),
        {
            "CHECK_INBOX": "fetch",
            "REPLY": "fetch",
            "COMPOSE": "memory_retrieve",
            "UNKNOWN": "memory_write"
        }
    )

    graph.add_conditional_edges(
        "memory_retrieve",
        memory_retrieve_router,
        {
            "draft": "draft",
            "compose": "compose"
        }
    )



    # Inbox Path
    graph.add_edge("fetch", "classify")
    graph.add_edge("classify", "inbox_review")

    # Review List Interactions
    graph.add_conditional_edges(
        "inbox_review",
        lambda s: s.get("user_action"),
        {
            "SUMMARIZE": "summarize",
            "REPLY": "draft",  # TODO: memory_retrieve
            "DONE": "memory_write"
        }
    )

    # graph.add_conditional_edges(
    #     "memory_retrieve",
    #     memory_retrieve_router,
    #     {
    #         "draft": "draft",
    #         "compose": "compose"
    #     }
    # )


    # Summarize loops back to list
    graph.add_edge("summarize", "inbox_review")

    # Compose Path (Iterative)
    graph.add_edge("compose", "review")
    graph.add_edge("draft", "review")


    def review_router(state):
        action = state.get("user_action")
        if action == "SEND":
            return "send"
        elif action == "EDIT":
            return "compose"
        elif action == "CANCEL":
            if state.get("emails"):
                return "inbox_review"
            return "memory_write"
        return "memory_write"


    graph.add_conditional_edges(
        "review",
        review_router,
        {
            "send": "send",
            "compose": "compose",
            "inbox_review": "inbox_review",
            "memory_write": "memory_write"
        }
    )


    # Send loops to inbox if in inbox mode, else END
    def after_send_router(state):
        if state.get("emails"):
            return "inbox_review"
        return END

    graph.add_conditional_edges(
        "send",
        after_send_router,
        {
            "inbox_review": "inbox_review",
            END: "memory_write"
        }
    )

    graph.add_edge("memory_write", END)

    
    # Legacy paths (Linear flow components) - unlikely to be hit directly now but kept for safety/topology validity if edge cases arise
    graph.add_edge("extract", "risk")
    graph.add_edge("risk", "approval")
    graph.add_edge("approval", "draft")

    return graph.compile()
