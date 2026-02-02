import json
from datetime import datetime
from app.classification.models import EmailMetadata
from app.classification.sender import SenderClassifier
from app.classification.intent import IntentScanner
from app.classification.priority import PriorityScorer

# Initialize classifiers once (or per call if stateful, but here they are stateless/config-based)
sender_classifier = SenderClassifier()
intent_scanner = IntentScanner()
priority_scorer = PriorityScorer() 

def classify_node(state):
    # Support for batch classification
    emails = state.get("emails", [])
    
    # If no batch, check single thread (legacy support or single item)
    if not emails and state.get("raw_thread"):
        emails = [state["raw_thread"]]

    processed_emails = []

    for email_dict in emails:
        # 1. Normalize Input to Metadata
        # Handle cases where email is dict or has different structure
        sender = email_dict.get("from") or ""
        subject = email_dict.get("subject") or ""
        body = email_dict.get("snippet") or "" # Use snippet as body proxy for efficiency, or full body if available
        # Date parsing (simplified)
        # Gmail API returns internalDate (timestamp ms). 
        # For now, let's assume current time or parse if available.
        msg_date = datetime.now() # Fallback
        
        metadata = EmailMetadata(
            sender=sender,
            subject=subject,
            body=body,
            date=msg_date,
            recipients=[], # Extract if needed
            has_attachments=False # Check if available
        )

        # 2. Run Classifiers
        sender_result = sender_classifier.classify(metadata)
        intent_result = intent_scanner.scan(subject, body)
        priority_result = priority_scorer.calculate_score(metadata, sender_result, intent_result)

        # 3. Construct Output Format (Compatible with existing graph)
        classification = {
            "priority": priority_result.priority_level.value,
            "category": "WORK", # Placeholder or derived from intent
            "intent": "WAIT", # Placeholder
            "confidence": sender_result.confidence,
            "reasoning": priority_result.reasoning
        }
        
        # Map specific intents if found
        if intent_result.intents:
            # Map first intent found
             classification["category"] = intent_result.intents[0].upper()
             
        if intent_result.action_required:
            classification["intent"] = "REPLY"

        # Attach classification to email object
        email_dict["classification"] = classification
        processed_emails.append(email_dict)

    state["emails"] = processed_emails
    
    # Legacy compatibility
    if state.get("raw_thread") and emails and emails[0].get("id") == state["raw_thread"].get("id"):
        state["classification"] = processed_emails[0]["classification"]
        
    return state
