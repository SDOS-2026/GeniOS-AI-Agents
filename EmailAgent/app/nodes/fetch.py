from app.gmail.client import get_gmail_service
from app.gmail.fetch import fetch_recent_emails

def fetch_node(state):
    """
    Fetches emails from Gmail API based on filters in state.
    """
    filters = state.get("filter_criteria", {})
    limit = filters.get("limit")
    if limit is None:
        limit = 5
    
    # Check if we should filter by unread/time_range? 
    # Current fetch_recent_emails is basic. We pass limit.
    # Advanced filtering logic can be added to fetch_recent_emails later 
    # or filtered in-memory here/classify node.
    
    # If filtering by priority, fetch more to increase chance of finding matches
    target_priority = filters.get("priority", "ANY")
    fetch_limit = limit
    if target_priority != "ANY":
        fetch_limit = max(limit * 3, 20) # Fetch at least 20 or 3x request
        
    print(f"DEBUG: Fetching {fetch_limit} emails (Limit: {limit})...")
    
    try:
        service = get_gmail_service()
        emails = fetch_recent_emails(service, max_results=fetch_limit)
    except Exception as e:
        print(f"Error fetching emails: {e}")
        emails = []
        
    state["emails"] = emails
    return state
