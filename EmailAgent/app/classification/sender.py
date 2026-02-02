"""
S1: Sender Classification
Identifies sender type and importance
"""
import logging
import re
from typing import List
from .config import Config
from .models import ClassificationResult, SenderType, EmailMetadata

logger = logging.getLogger(__name__)


class SenderClassifier:
    """Classifies email senders"""
    
    def __init__(self):
        self.vip_domains = Config.VIP_DOMAINS
        self.vip_emails: List[str] = Config.VIP_EMAILS # Loaded from config
        self.known_vendors: List[str] = []  # Can be loaded from database
        self.team_domains: List[str] = ["example.com", "internal.com"]  # Internal company domains
    
    def classify(self, metadata: EmailMetadata) -> ClassificationResult:
        """
        S1: Sender Classification
        
        Analyzes sender and determines their type and importance
        """
        sender_email = metadata.sender
        sender_domain = self._extract_domain(sender_email)
        
        logger.debug(f"Classifying sender: {sender_email}")
        
        # Determine sender type
        sender_type = self._determine_sender_type(sender_email, sender_domain)
        is_vip = self._is_vip(sender_email, sender_domain)
        is_internal = sender_domain in self.team_domains
        
        # Calculate confidence
        confidence = self._calculate_confidence(sender_type, is_vip)
        
        # Generate notes
        notes = self._generate_classification_notes(
            sender_type, is_vip, is_internal, sender_domain
        )
        
        result = ClassificationResult(
            sender_type=sender_type,
            sender_email=sender_email,
            sender_domain=sender_domain,
            is_vip=is_vip,
            is_internal=is_internal,
            confidence=confidence,
            notes=notes
        )
        
        logger.info(f"Classified {sender_email} as {sender_type.value} (VIP: {is_vip})")
        return result
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        email = email or ""
        match = re.search(r'@([\w\.-]+)', email)
        return match.group(1) if match else ""
    
    def _determine_sender_type(self, email: str, domain: str) -> SenderType:
        """Determine the type of sender"""
        email = email or ""
        domain = domain or ""
        # Check if VIP
        if email.lower() in [v.lower() for v in self.vip_emails]:
            return SenderType.VIP
        
        if domain in self.vip_domains:
            return SenderType.VIP
        
        # Check if internal team
        if domain in self.team_domains:
            return SenderType.TEAM
        
        # Check known vendors
        if email.lower() in [v.lower() for v in self.known_vendors]:
            return SenderType.VENDOR
        
        # Check for common spam patterns
        if self._looks_like_spam(email, domain):
            return SenderType.SPAM
        
        # Check for customer-like patterns
        if self._looks_like_customer(email, domain):
            return SenderType.CUSTOMER
        
        return SenderType.UNKNOWN
    
    def _is_vip(self, email: str, domain: str) -> bool:
        """Check if sender is VIP"""
        email = email or ""
        domain = domain or ""
        # Explicit VIP list
        if email.lower() in [v.lower() for v in self.vip_emails]:
            return True
        
        # VIP domain
        if domain in self.vip_domains:
            return True
        
        # VIP keywords in name (CEO, founder, board, etc.)
        vip_keywords = ['ceo', 'founder', 'president', 'board', 'director', 'vp', 'cfo', 'cto']
        email_lower = email.lower()
        
        for keyword in vip_keywords:
            if keyword in email_lower:
                return True
        
        return False
    
    def _looks_like_spam(self, email: str, domain: str) -> bool:
        """Check if sender looks like spam"""
        email = email or ""
        domain = domain or ""
        
        # Whitelist trusted domains - never mark as spam even if noreply
        trusted_domains = ['github.com', 'linear.app', 'slack.com', 'google.com', 'linkedin.com']
        if domain in trusted_domains:
            return False
            
        spam_patterns = [
            'noreply', 'no-reply', 'donotreply', 'notification',
            'marketing', 'newsletter', 'promo', 'deals'
        ]
        
        email_lower = email.lower()
        for pattern in spam_patterns:
            if pattern in email_lower:
                return True
        
        # Generic free email providers + random chars pattern
        free_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        if domain in free_providers:
            # Check for random character patterns - relax to >5 digits to avoid false positives
            local_part = email.split('@')[0]
            if len(local_part) > 15 or re.search(r'\d{6,}', local_part):
                return True
        
        return False
    
    def _looks_like_customer(self, email: str, domain: str) -> bool:
        """Check if sender looks like a customer"""
        # Has professional domain (not free email)
        free_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        
        if domain not in free_providers and '.' in domain:
            return True
        
        return False
    
    def _calculate_confidence(self, sender_type: SenderType, is_vip: bool) -> float:
        """Calculate classification confidence"""
        if is_vip:
            return 1.0
        
        confidence_map = {
            SenderType.VIP: 1.0,
            SenderType.TEAM: 0.95,
            SenderType.VENDOR: 0.80,
            SenderType.CUSTOMER: 0.70,
            SenderType.SPAM: 0.85,
            SenderType.UNKNOWN: 0.50
        }
        
        return confidence_map.get(sender_type, 0.5)
    
    def _generate_classification_notes(self, sender_type: SenderType, 
                                       is_vip: bool, is_internal: bool,
                                       domain: str) -> str:
        """Generate human-readable classification notes"""
        notes = []
        
        if is_vip:
            notes.append("⭐ VIP sender")
        
        if is_internal:
            notes.append("🏢 Internal team member")
        
        notes.append(f"Type: {sender_type.value}")
        notes.append(f"Domain: {domain}")
        
        return " | ".join(notes)
    
    def add_vip(self, email: str):
        """Add email to VIP list"""
        if email not in self.vip_emails:
            self.vip_emails.append(email)
            logger.info(f"Added {email} to VIP list")
    
    def add_vendor(self, email: str):
        """Add email to vendor list"""
        if email not in self.known_vendors:
            self.known_vendors.append(email)
            logger.info(f"Added {email} to vendor list")
