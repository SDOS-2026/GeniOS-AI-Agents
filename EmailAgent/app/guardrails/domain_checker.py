"""
G2: Domain Restriction Check
"""
import logging
from typing import List
from app.classification.config import Config
from app.classification.models import ProcessedEmail, SecurityFlag

logger = logging.getLogger(__name__)


class DomainChecker:
    """Checks email domains against allowed/blocked lists"""
    
    def __init__(self):
        self.allowed_domains = Config.ALLOWED_DOMAINS
        self.blocked_domains = Config.BLOCKED_DOMAINS
        self.internal_domains = set()  # Add company internal domains
    
    def check_domain_restrictions(self, email: ProcessedEmail) -> bool:
        """
        G2: Domain Restriction Check
        
        Validates recipient domains against policy
        
        Returns: True if approved, False if restricted
        """
        logger.debug(f"Checking domain restrictions for: {email.metadata.subject}")
        
        # If no draft, nothing to check
        if not email.draft_reply:
            return True
        
        # Get all recipients
        all_recipients = (
            email.draft_reply.recipients +
            email.draft_reply.cc
        )
        
        if not all_recipients:
            return True
        
        # Extract domains
        recipient_domains = [self._extract_domain(r) for r in all_recipients]
        
        # Check each domain
        violations = []
        
        for domain in recipient_domains:
            # Check if blocked
            if domain in self.blocked_domains:
                violations.append(f"Blocked domain: {domain}")
                logger.warning(f"⚠️ Blocked domain detected: {domain}")
                continue
            
            # Check if external (not in allowed list)
            is_external = domain not in self.allowed_domains and domain not in self.internal_domains
            
            # If external and email has confidential data, block it
            if is_external and email.has_pii:
                violations.append(f"External domain with PII: {domain}")
                logger.warning(f"⚠️ Cannot send PII to external domain: {domain}")
        
        # If violations found, mark as not approved
        if violations:
            flag = SecurityFlag(
                flag_type="domain_restriction",
                severity="high",
                description="Domain policy violation",
                details={
                    "violations": violations,
                    "recipient_domains": recipient_domains
                },
                blocks_sending=True
            )
            email.security_flags.append(flag)
            email.domain_approved = False
            
            logger.error(f"🚨 DOMAIN VIOLATIONS: {len(violations)}")
            return False
        
        email.domain_approved = True
        logger.debug("✓ Domain check passed")
        return True
    
    def _extract_domain(self, email_address: str) -> str:
        """Extract domain from email address"""
        import re
        match = re.search(r'@([\w\.-]+)', email_address)
        return match.group(1).lower() if match else ""
    
    def is_external_email(self, email: ProcessedEmail) -> bool:
        """Check if email is going to external recipients"""
        if not email.draft_reply:
            return False
        
        recipients = email.draft_reply.recipients + email.draft_reply.cc
        
        for recipient in recipients:
            domain = self._extract_domain(recipient)
            if domain not in self.allowed_domains and domain not in self.internal_domains:
                return True
        
        return False
    
    def add_allowed_domain(self, domain: str):
        """Add domain to allowed list"""
        self.allowed_domains.add(domain.lower())
        logger.info(f"Added allowed domain: {domain}")
    
    def add_blocked_domain(self, domain: str):
        """Add domain to blocked list"""
        self.blocked_domains.add(domain.lower())
        logger.info(f"Added blocked domain: {domain}")
