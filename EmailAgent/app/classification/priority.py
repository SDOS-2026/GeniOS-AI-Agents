"""
S3: Priority Scoring Engine
Calculates priority score based on multiple factors
"""
import logging
from datetime import datetime, timedelta
from .config import Config
from .models import (
    PriorityScore, PriorityLevel, EmailMetadata,
    ClassificationResult, IntentDetection
)

logger = logging.getLogger(__name__)


class PriorityScorer:
    """Calculates email priority scores"""
    
    def __init__(self):
        self.threshold = Config.PRIORITY_THRESHOLD
    
    def calculate_score(self,
                       metadata: EmailMetadata,
                       classification: ClassificationResult,
                       intent: IntentDetection) -> PriorityScore:
        """
        S3: Priority Scoring Engine
        
        Calculates composite priority score (0-100) based on:
        - Sender importance (VIP, team, etc.)
        - Urgency keywords
        - Deadline proximity
        - Question/action required
        - Email age
        """
        logger.debug(f"Calculating priority for: {metadata.subject}")
        
        factors = {}
        score = 0
        
        # Factor 1: Sender importance (0-40 points)
        sender_score = self._score_sender(classification)
        
        # Boost sender score for complaints - treat as at least 'customer' level importance
        if 'complaint' in intent.intents:
            sender_score = max(sender_score, 25)
            
        if not intent.urgency_keywords and not intent.action_required and 'complaint' not in intent.intents and 'invitation' not in intent.intents:
            sender_score = min(sender_score, 20)
        factors['sender_importance'] = sender_score
        score += sender_score
        
        # Factor 2: Urgency keywords (0-35 points - increased from 30)
        urgency_score = self._score_urgency(intent)
        factors['urgency_keywords'] = urgency_score
        score += urgency_score
        
        # Factor 3: Action required (0-15 points)
        action_score = self._score_action(intent)
        factors['action_required'] = action_score
        score += action_score
        
        # Factor 4: Email age (0-10 points)
        age_score = self._score_age(metadata.date)
        factors['email_age'] = age_score
        score += age_score
        
        # Factor 5: Thread context (0-15 points - increased from 10)
        thread_score = self._score_thread(metadata)
        factors['thread_context'] = thread_score
        score += thread_score
        
        # Factor 6: Special categories (0-20 points - increased from 5)
        category_score = self._score_category(intent)
        factors['special_category'] = category_score
        score += category_score
        
        # Factor 7: Business context and impact (0-10 points NEW)
        business_score = self._score_business_context(metadata, intent)
        factors['business_impact'] = business_score
        score += business_score
        
        # Urgency Override: If urgency is high, push to at least MEDIUM priority
        if intent.urgency_score >= 18:
            score = max(score, 50)
            logger.info("Urgency override triggered: Score boosted to minimum 50")
        
        # Critical urgency = HIGH priority minimum
        if intent.urgency_score >= 25:
            score = max(score, 70)
            logger.info("Critical urgency: Score boosted to minimum 70")
        
        # Multiple signals = compound priority
        high_priority_signals = 0
        if intent.urgency_score >= 15:
            high_priority_signals += 1
        if intent.action_required and intent.question_detected:
            high_priority_signals += 1
        if sender_score >= 30:
            high_priority_signals += 1
        if 'complaint' in intent.intents or 'legal' in intent.intents:
            high_priority_signals += 1
        if category_score >= 15:
            high_priority_signals += 1
        
        # If multiple high-priority signals, boost score
        if high_priority_signals >= 3:
            score = int(score * 1.15)  # 15% boost for multiple signals
            logger.info(f"Multiple priority signals ({high_priority_signals}): Score boosted by 15%")
        
        # Ensure score is within 0-150 (increased max from 100)
        score = max(0, min(150, int(score)))
        
        # Determine priority level
        priority_level = self._determine_level(score)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(score, factors, priority_level)
        
        result = PriorityScore(
            score=score,
            priority_level=priority_level,
            factors=factors,
            reasoning=reasoning
        )
        
        logger.info(f"Priority score: {score}/100 ({priority_level.value})")
        return result
    
    def _score_sender(self, classification: ClassificationResult) -> int:
        """Score based on sender importance (0-40)"""
        if classification.is_vip:
            return 40
        
        sender_scores = {
            'vip': 40,
            'team': 30,
            'customer': 25,
            'vendor': 15,
            'unknown': 5,
            'spam': 0
        }
        
        return sender_scores.get(classification.sender_type.value, 5)
    
    def _score_urgency(self, intent: IntentDetection) -> int:
        """Score based on urgency keywords (0-35 points)"""
        return min(intent.urgency_score, 35)
    
    def _score_action(self, intent: IntentDetection) -> int:
        """Score based on action required (0-15)"""
        score = 0

        if intent.action_required:
            score += 8

        if intent.question_detected:
            score += 4

        if intent.action_required and intent.question_detected:
            score += 3

        if intent.is_follow_up:
            score += 3

        return min(score, 15)
    
    def _score_age(self, email_date: datetime) -> int:
        """Score based on email age (0-10) - newer = higher"""
        if not email_date:
            return 0
            
        now = datetime.now(email_date.tzinfo) if email_date.tzinfo else datetime.now()
        age = now - email_date
        
        # Less than 1 hour = 10 points
        if age < timedelta(hours=1):
            return 10
        # Less than 4 hours = 8 points
        elif age < timedelta(hours=4):
            return 8
        # Less than 24 hours = 5 points
        elif age < timedelta(days=1):
            return 5
        # Less than 3 days = 2 points
        elif age < timedelta(days=3):
            return 2
        # Older = 0 points
        else:
            return 0
    
    def _score_thread(self, metadata: EmailMetadata) -> int:
        """Score based on thread context and content analysis (0-15)"""
        score = 0
        
        # If it's a reply (has Re: in subject) - ongoing conversation
        if metadata.subject.lower().startswith('re:'):
            score += 5
        
        # Forward chains might be informational but less urgent
        if metadata.subject.lower().startswith('fwd:'):
            score += 1
        
        # If user is in To: (not just CC)
        if metadata.recipients:
            score += 3
        
        # Has attachments - could be important documents
        if metadata.has_attachments:
            score += 4
            # Check if subject mentions attachment/doc/file
            subject_lower = metadata.subject.lower()
            if any(word in subject_lower for word in ['attached', 'document', 'file', 'contract', 'agreement', 'invoice']):
                score += 2
        
        # Long subject lines often contain more context/urgency
        if len(metadata.subject) > 50:
            score += 1
        
        return min(score, 15)
    
    def _score_category(self, intent: IntentDetection) -> int:
        """Score based on special categories with nuanced priority (0-20)"""
        score = 0
        
        # Critical categories (customer-facing, legal, complaints)
        if 'complaint' in intent.intents:
            score += 18  # Customer complaints = top priority
            # Multiple complaint keywords = even more critical
            if intent.urgency_score > 10:
                score += 2
        
        # High priority categories
        if 'legal' in intent.intents:
            score += 12  # Legal matters can't wait
        if 'finance' in intent.intents:
            score += 10  # Money matters important
        
        # IT/Security issues
        if 'it' in intent.intents:
            score += 8
            # If it's access/security related, boost more
            if intent.urgency_score > 8:
                score += 4
        
        # HR and invitations
        if 'invitation' in intent.intents:
            score += 8  # Invitations time-sensitive
        if 'hr' in intent.intents:
            score += 6
        
        # Meetings - depends on timing
        if 'meeting' in intent.intents:
            score += 5
            # If it's urgent meeting scheduling
            if any(kw in intent.urgency_keywords for kw in ['today', 'tomorrow', 'asap']):
                score += 5
        
        return min(score, 20)
    
    def _score_business_context(self, metadata: EmailMetadata, intent: IntentDetection) -> int:
        """NEW: Score business impact and contextual importance (0-10 points)"""
        score = 0
        text = (metadata.subject + " " + (metadata.body or "")).lower()
        
        # Check for automated/low-value emails (deduct points)
        if any(word in text for word in ['newsletter', 'unsubscribe', 'automated', 'no-reply']):
            score -= 5
        
        # Check for business-critical keywords
        critical_business = ['revenue', 'contract', 'deal', 'legal', 'lawsuit', 
                           'customer complaint', 'data breach', 'security incident']
        if any(word in text for word in critical_business):
            score += 8
        
        # Check for time-sensitive business ops
        time_sensitive = ['deadline', 'by eod', 'by end of', 'expires', 'due date']
        if any(phrase in text for phrase in time_sensitive):
            score += 5
        
        # Check recipient count (mass emails = lower priority)
        if hasattr(metadata, 'recipients') and len(metadata.recipients) > 20:
            score -= 3
        
        return max(-5, min(score, 10))  # Range: -5 to 10
    
    def _determine_level(self, score: int) -> PriorityLevel:
        """
        S4: High Priority? Decision
        
        Determines priority level based on score with refined thresholds
        HIGH: 75-150 (requires immediate attention)
        MEDIUM: 50-74 (respond within day)
        LOW: 30-49 (can wait, but needs response)
        NOT_REQUIRED: 0-29 (FYI, optional)
        """
        if score >= 75:  # Increased from 70
            return PriorityLevel.HIGH
        elif score >= 50:  # Increased from 45
            return PriorityLevel.MEDIUM
        elif score >= 30:  # Increased from 25
            return PriorityLevel.LOW
        else:
            return PriorityLevel.NOT_REQUIRED
    
    def _generate_reasoning(self, score: int, factors: dict,
                           level: PriorityLevel) -> str:
        """Generate detailed, actionable reasoning for priority score"""
        reasons = []
        
        # Sort factors by score
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        
        # Add top contributors with details
        for factor_name, factor_score in sorted_factors:
            if factor_score > 0:
                reason = self._factor_to_reason(factor_name, factor_score)
                if reason:
                    reasons.append(reason)
        
        # Create priority indicator
        if level == PriorityLevel.HIGH:
            indicator = "🔴 HIGH"
        elif level == PriorityLevel.MEDIUM:
            indicator = "🟡 MEDIUM"
        elif level == PriorityLevel.LOW:
            indicator = "🟢 LOW"
        else:
            indicator = "⚪ NOT REQUIRED"
        
        reasoning = f"{indicator} ({score}/150)"
        
        if reasons:
            # Show top reasons
            top_reasons = reasons[:4]  # Increased from 3 to 4
            reasoning += " | " + ", ".join(top_reasons)
        
        return reasoning
    
    def _factor_to_reason(self, factor_name: str, score: int) -> str:
        """Convert factor name and score to readable reason"""
        reason_map = {
            'sender_importance': f"Important sender (+{score})",
            'urgency_keywords': f"Urgent keywords (+{score})",
            'action_required': f"Action needed (+{score})",
            'email_age': f"Recent email (+{score})",
            'thread_context': f"Active thread (+{score})",
            'special_category': f"Priority category (+{score})",
            'business_impact': f"Business impact (+{score})"
        }
        
        return reason_map.get(factor_name, "")
