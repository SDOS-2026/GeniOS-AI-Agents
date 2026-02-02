"""
G3: Safe Tone Enforcement
"""
import logging
import re
from typing import List, Tuple
from app.classification.models import ProcessedEmail, SecurityFlag

logger = logging.getLogger(__name__)


class ToneEnforcer:
    """Enforces safe, professional tone in email drafts"""
    
    def __init__(self):
        # Aggressive/risky words and phrases
        self.aggressive_words = [
            'demand', 'require', 'must', 'immediately', 'unacceptable',
            'disappointed', 'frustrated', 'angry', 'furious', 'outraged'
        ]
        
        self.risky_phrases = [
            'guarantee', 'promise', 'assured', 'definitely will',
            'never', 'always', 'impossible', 'absolutely',
            'you should', 'you must', 'you need to'
        ]
        
        # Legal liability phrases
        self.liability_phrases = [
            'we guarantee', 'we promise', 'legally binding',
            'we assure', 'without exception', 'in all cases'
        ]
        
        # Unprofessional language
        self.unprofessional = [
            'asap', 'fyi', 'btw', 'lol', 'omg', 'wtf',
            'yeah', 'nope', 'gonna', 'wanna', 'gotta'
        ]
    
    def enforce_safe_tone(self, email: ProcessedEmail) -> Tuple[bool, List[str]]:
        """
        G3: Safe Tone Enforcement
        
        Analyzes draft for risky or unprofessional language
        
        Returns: (tone_approved, list_of_issues)
        """
        logger.debug(f"Checking tone for: {email.metadata.subject}")
        
        # If no draft, nothing to check
        if not email.draft_reply:
            return True, []
        
        issues = []
        
        draft_text = f"{email.draft_reply.subject}\n{email.draft_reply.body}".lower()
        
        # Check for aggressive words
        for word in self.aggressive_words:
            if word in draft_text:
                issues.append(f"Aggressive language: '{word}'")
                logger.warning(f"⚠️ Aggressive word found: '{word}'")
        
        # Check for risky phrases
        for phrase in self.risky_phrases:
            if phrase in draft_text:
                issues.append(f"Risky phrase: '{phrase}'")
                logger.warning(f"⚠️ Risky phrase found: '{phrase}'")
        
        # Check for liability phrases
        for phrase in self.liability_phrases:
            if phrase in draft_text:
                issues.append(f"Legal liability: '{phrase}'")
                logger.warning(f"⚠️ Liability phrase found: '{phrase}'")
        
        # Check for unprofessional language
        for word in self.unprofessional:
            if f" {word} " in f" {draft_text} ":  # Word boundaries
                issues.append(f"Unprofessional: '{word}'")
                logger.warning(f"⚠️ Unprofessional word found: '{word}'")
        
        # Check for excessive exclamation marks
        exclamation_count = draft_text.count('!')
        if exclamation_count > 2:
            issues.append(f"Excessive exclamation marks ({exclamation_count})")
            logger.warning(f"⚠️ Too many exclamation marks: {exclamation_count}")
        
        # Check for all caps words (shouting)
        words = draft_text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        if len(caps_words) > 1:
            issues.append(f"All-caps words (appears like shouting)")
            logger.warning(f"⚠️ All-caps words found: {caps_words}")
        
        # Determine if tone is approved
        tone_approved = len(issues) == 0
        
        if not tone_approved:
            # Add security flag
            severity = "high" if any('liability' in i or 'Aggressive' in i for i in issues) else "medium"
            
            flag = SecurityFlag(
                flag_type="tone_violation",
                severity=severity,
                description=f"Tone issues detected: {len(issues)} problem(s)",
                details={"issues": issues},
                blocks_sending=True
            )
            email.security_flags.append(flag)
            email.tone_approved = False
            
            logger.warning(f"🚨 TONE VIOLATIONS: {len(issues)}")
        else:
            email.tone_approved = True
            logger.debug("✓ Tone check passed")
        
        return tone_approved, issues
    
    def suggest_alternatives(self, problematic_text: str) -> str:
        """Suggest professional alternatives for problematic text"""
        alternatives = {
            'demand': 'request',
            'require': 'need',
            'must': 'should',
            'immediately': 'as soon as possible',
            'unacceptable': 'concerning',
            'asap': 'as soon as possible',
            'fyi': 'for your information',
            'btw': 'by the way'
        }
        
        suggestion = problematic_text.lower()
        for word, alternative in alternatives.items():
            suggestion = suggestion.replace(word, alternative)
        
        return suggestion
