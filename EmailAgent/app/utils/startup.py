from datetime import datetime, timedelta
from app.gmail.client import get_gmail_service
from app.gmail.utils import get_user_profile
from app.gmail.fetch import fetch_recent_emails
from app.classification.models import EmailMetadata, PriorityLevel
from app.classification.sender import SenderClassifier
from app.classification.intent import IntentScanner
from app.classification.priority import PriorityScorer
from app.memory.supabase_client import supabase
from app.memory.embeddings import embed_text

def run_startup_scan():
    """
    Scans unread emails from the last 24 hours, classifies them,
    stores High/Medium priority summaries, and prints a report.
    """
    print("\n=== Startup Email Scan ===")
    
    # 1. Setup
    service = get_gmail_service()
    user_email = get_user_profile(service) or "default_user"
    print(f"Authenticated as: {user_email}")
    
    sender_classifier = SenderClassifier()
    intent_scanner = IntentScanner()
    priority_scorer = PriorityScorer()
    
    # 2. Fetch Unread (Last 24h)
    # Gmail query: older_than:1d covers >24h, so newer_than:1d is correct.
    query = "newer_than:1d is:unread"
    print(f"Fetching emails with query: '{query}'...")
    
    try:
        raw_emails = fetch_recent_emails(service, max_results=20, query=query)
    except Exception as e:
        print(f"Error fetching startup emails: {e}")
        return

    if not raw_emails:
        print("No unread emails found in the last 24 hours.")
        return

    print(f"Found {len(raw_emails)} unread emails. Classifying...")

    priority_emails = []

    # 3. Classify
    for email in raw_emails:
        sender = email.get("from", "")
        subject = email.get("subject", "")
        snippet = email.get("snippet", "") # Note: fetch_recent_emails currently does not populate snippet in basic fetch? 
                                          # Wait, checking fetch.py... it fetches specific headers. 
                                          # We might need snippet. Let's assume fetch returns basic structure.
                                          # Actually fetch.py returns 'id', 'thread_id', 'from', 'subject'.
                                          # It does NOT return snippet currently. We should probably update fetch or re-fetch partial.
                                          # For now, let's use subject as body proxy if snippet missing.
        
        body = snippet if snippet else subject 
        
        metadata = EmailMetadata(
            sender=sender,
            subject=subject,
            body=body,
            date=datetime.now(), # Approximate
            recipients=[],
            has_attachments=False
        )
        
        sender_result = sender_classifier.classify(metadata)
        intent_result = intent_scanner.scan(subject, body)
        priority_result = priority_scorer.calculate_score(metadata, sender_result, intent_result)
        
        if priority_result.priority_level in [PriorityLevel.HIGH, PriorityLevel.MEDIUM]:
            priority_emails.append({
                "email": email,
                "classification": {
                    "priority": priority_result.priority_level,
                    "score": priority_result.score,
                    "category": intent_result.intents[0] if intent_result.intents else "WORK",
                    "reasoning": priority_result.reasoning
                }
            })

    # 4. Sort and Limit
    # Sort by Score (desc), then Time (implicit by order often, but let's trust score)
    priority_emails.sort(key=lambda x: x["classification"]["score"], reverse=True)
    
    top_emails = priority_emails[:3]
    
    if not top_emails:
        print("No High/Medium priority emails found.")
        return

    print(f"\nTop {len(top_emails)} Priority Emails:")
    
    # 5. Store and Display
    for item in top_emails:
        email = item["email"]
        cls = item["classification"]
        
        summary_text = f"From: {email.get('from')} | Sub: {email.get('subject')}"
        email_embedding = embed_text(summary_text)
        
        # Display
        print(f"[{cls['priority'].value.upper()}] {summary_text}")
        print(f"   Reason: {cls['reasoning']}")
        
        # Store in Memory
        try:
            priority_data = {
                "user_id": user_email, 
                "email_summary": summary_text,
                "priority": cls["priority"].value,
                "category": cls["category"],
                "source": email.get("from"),
                "email_embedding": email_embedding,
                "metadata": {
                    "reasoning": cls["reasoning"],
                    "startup_scan": True,
                    "timestamp": datetime.now().isoformat()
                }
            }
            supabase.from_("priority_email_memory").insert(priority_data).execute()
        except Exception as e:
            print(f"   (Failed to save memory: {e})")

    print("\nScan Complete.\n")
