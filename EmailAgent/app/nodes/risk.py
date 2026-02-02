from app.policy.rules import RISK_FLAGS


def risk_node(state):
    flags = []

    classification = state.get("classification", {})
    extracted = state.get("extracted_details", {})
    thread = state.get("raw_thread", {})

    subject = str(thread.get("subject", "")).lower()
    body = str(thread.get("body", "")).lower()
    sender = str(thread.get("from", "")).lower()

    # --- Rule 1: Legal / financial category ---
    if classification.get("category") == "LEGAL":
        flags.append("LEGAL_COMMITMENT")

    if classification.get("category") == "FINANCE":
        flags.append("FINANCIAL_COMMITMENT")

    # --- Rule 2: External sender ---
    if sender and not sender.endswith("@yourcompany.com"):
        flags.append("EXTERNAL_SENDER")

    # --- Rule 3: Ambiguous deadlines ---
    ambiguities = extracted.get("ambiguities", [])
    if ambiguities:
        flags.append("AMBIGUOUS_DEADLINE")

    # --- Rule 4: Simple PII heuristic (very conservative) ---
    pii_keywords = ["aadhaar", "ssn", "passport", "pan", "bank", "account number"]
    if any(k in body for k in pii_keywords):
        flags.append("PII_DETECTED")

    state["risk_flags"] = list(set(flags))  # deduplicate
    return state
