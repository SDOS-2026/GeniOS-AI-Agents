"""
G1: PII and Confidential Data Detection
"""
import logging
import re
from typing import List, Tuple
from app.classification.models import ProcessedEmail, SecurityFlag

logger = logging.getLogger(__name__)


class PIIDetector:
    """Detects Personally Identifiable Information and confidential data"""
    
    def __init__(self):
        # Regex patterns for PII
        self.patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'password': r'(?i)(password|passwd|pwd)[\s:=]+[^\s]+',
        }
        
        # Confidential keywords
        self.confidential_keywords = [
            'confidential', 'proprietary', 'internal only',
            'do not share', 'restricted', 'classified',
            'trade secret', 'sensitive'
        ]
    
    def detect_pii_and_confidential(self, email: ProcessedEmail) -> Tuple[bool, List[str]]:
        """
        G1: PII and Confidential Data Detection
        
        Scans email for PII and confidential information
        
        Returns: (has_pii, list_of_detected_types)
        """
        logger.debug(f"Scanning for PII: {email.metadata.subject}")
        
        detected = []
        
        # Scan email content
        text = f"{email.metadata.subject}\n{email.metadata.body_text}"
        
        # Check for PII patterns
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected.append(pii_type)
                logger.warning(f"⚠️ Detected {pii_type}: {len(matches)} occurrence(s)")
        
        # Check draft reply if exists
        if email.draft_reply:
            draft_text = f"{email.draft_reply.subject}\n{email.draft_reply.body}"
            for pii_type, pattern in self.patterns.items():
                matches = re.findall(pattern, draft_text)
                if matches and pii_type not in detected:
                    detected.append(f"{pii_type}_in_draft")
                    logger.warning(f"⚠️ Detected {pii_type} in DRAFT: {len(matches)} occurrence(s)")
        
        # Check for confidential keywords
        text_lower = text.lower()
        for keyword in self.confidential_keywords:
            if keyword in text_lower:
                detected.append('confidential_marker')
                logger.warning(f"⚠️ Confidential marker found: '{keyword}'")
                break
        
        has_pii = len(detected) > 0
        
        if has_pii:
            # Add security flag
            flag = SecurityFlag(
                flag_type="pii_detected",
                severity="high" if any('ssn' in d or 'credit_card' in d for d in detected) else "medium",
                description=f"PII or confidential data detected: {', '.join(detected)}",
                details={"detected_types": detected},
                blocks_sending=True
            )
            email.security_flags.append(flag)
            email.has_pii = True
            
            logger.warning(f"🚨 PII DETECTED: {', '.join(detected)}")
        else:
            logger.debug("✓ No PII detected")
        
        return has_pii, detected
    
    def anonymize_text(self, text: str) -> str:
        """Anonymize PII in text (for logging/display purposes)"""
        anonymized = text
        
        # Replace SSN
        anonymized = re.sub(self.patterns['ssn'], '[SSN]', anonymized)
        
        # Replace credit card
        anonymized = re.sub(self.patterns['credit_card'], '[CREDIT_CARD]', anonymized)
        
        # Replace phone
        anonymized = re.sub(self.patterns['phone'], 'MOBILE_NUMBER', anonymized)
        
        # Replace API keys
        anonymized = re.sub(self.patterns['api_key'], 'API_KEY', anonymized)
        
        # Replace IP
        anonymized = re.sub(self.patterns['ip_address'], '[IP_ADDRESS]', anonymized)

        # Replace Email
        # anonymized = re.sub(self.patterns['email'], '[EMAIL]', anonymized) 
        
        return anonymized
