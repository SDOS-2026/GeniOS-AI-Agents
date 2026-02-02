import sys
from app.graph.graph import build_graph
from app.utils.startup import run_startup_scan
from app.gmail.utils import get_user_profile
from app.gmail.client import get_gmail_service
# from app.graph.state import EmailAgentState

def run_interactive_mode():
    print("=== EMAIL AGENT INTERACTIVE MODE ===")
    print("Type 'exit' to quit.")
    
    # Run Startup Scan
    run_startup_scan()
    
    # Compile graph once
    try:
        graph = build_graph()
    except Exception as e:
        print(f"Error building graph: {e}")
        return

    while True:
        try:

            # user_input = input("\nYou (h for help menu): ").strip()
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            # if user_input.strip().lower() == "h":
            #     print("h : help menu (this)\nthink on : show reasoning\nthink off : stop showing reasoning\n exit/quit/q : exit")
            #     continue

            # if user_input.strip().lower() == "think on":
            #     state["show_reasoning"] = True
            #     state["reasoning"] = []   # start fresh
            #     print("Reasoning enabled.")
            #     continue

            # if user_input.strip().lower() == "think off":
            #     state["show_reasoning"] = False
            #     state["reasoning"] = []
            #     print("Reasoning disabled.")
            #     continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                sys.exit(0)

            print("Thinking...")
            
            # Unified Entry Point
            # The graph handles Intent -> Logic -> Action
            
            # Fetch current user email for context
            try:
                service = get_gmail_service()
                current_user_email = get_user_profile(service) or "default_user"
            except Exception:
                current_user_email = "default_user"

            initial_state = {
                "user_prompt": user_input,
                "user_id": current_user_email,
                "thread_id": "unified_session",
                "emails": [], # Clear previous email context
                "filter_criteria": {},
                "mode": "UNKNOWN" # Will be set by input_agent
            }

            try:
                graph.invoke(initial_state)
            except Exception as e:
                print(f"Error executing agent: {e}")
                import traceback
                traceback.print_exc()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_interactive_mode()
