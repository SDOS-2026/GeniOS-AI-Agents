"""
Unit Tests: Daily Attention Agent — Signal Normalization & Scoring
Tests Gmail/Calendar normalizers, rule scoring, and priority levels.

Run with: pytest test_daa_signals.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone


# ==============================================================
# FIXTURES
# ==============================================================

def _gmail_thread(thread_id="t1", subject="Test Email", sender="user@example.com",
                  snippet="Here is the message.", days_old=0):
    """Build a minimal Gmail thread dict matching real Gmail API structure."""
    date_str = (datetime.now(timezone.utc) - timedelta(days=days_old)).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    return {
        "id": thread_id,
        "messages": [{
            "payload": {
                "headers": [
                    {"name": "Subject", "value": subject},
                    {"name": "From", "value": sender},
                    {"name": "Date", "value": date_str},
                ]
            },
            "snippet": snippet,
        }]
    }


def _calendar_event(event_id="e1", summary="Team Meeting",
                    start_offset_hours=2, duration_hours=1,
                    attendee_count=3, has_link=True,
                    description="Agenda: Q2 review"):
    """Build a minimal Calendar event dict matching Google Calendar API."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=start_offset_hours)
    end = start + timedelta(hours=duration_hours)
    event = {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "description": description,
        "attendees": [{"email": f"person{i}@company.com"} for i in range(attendee_count)],
        "organizer": {"email": "organizer@company.com"},
        "htmlLink": "https://calendar.google.com/event?id=e1",
    }
    if has_link:
        event["hangoutLink"] = "https://meet.google.com/abc-xyz"
    return event


# ==============================================================
# GMAIL NORMALIZER TESTS
# ==============================================================

class TestGmailNormalizer:

    def test_normalize_single_thread(self):
        """normalize_gmail_threads must convert one thread into one UnifiedSignal."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread()]
        signals = normalize_gmail_threads(threads)

        assert len(signals) == 1
        assert signals[0].signal_type == "EMAIL_THREAD"
        assert signals[0].source_tool == "gmail"

    def test_normalize_extracts_subject(self):
        """Signal title must match the email's Subject header."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread(subject="Important Update")]
        signals = normalize_gmail_threads(threads)

        assert signals[0].title == "Important Update"

    def test_normalize_extracts_sender(self):
        """Signal owner must match the 'From' header."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread(sender="boss@company.com")]
        signals = normalize_gmail_threads(threads)

        assert signals[0].owner == "boss@company.com"

    def test_normalize_detects_requires_action_from_question(self):
        """Email with '?' in subject must have requires_action=True."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread(subject="Can you attend the meeting?")]
        signals = normalize_gmail_threads(threads)

        assert signals[0].requires_action is True

    def test_normalize_skips_thread_with_no_messages(self):
        """Threads with empty 'messages' list must be skipped."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [{"id": "empty", "messages": []}]
        signals = normalize_gmail_threads(threads)

        assert len(signals) == 0

    def test_normalize_multiple_threads(self):
        """normalize_gmail_threads must handle multiple threads correctly."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread(f"t{i}", f"Subject {i}") for i in range(5)]
        signals = normalize_gmail_threads(threads)

        assert len(signals) == 5
        titles = {s.title for s in signals}
        assert titles == {f"Subject {i}" for i in range(5)}

    def test_normalized_signal_is_immutable(self):
        """UnifiedSignal should be immutable (frozen Pydantic model)."""
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads

        threads = [_gmail_thread()]
        signal = normalize_gmail_threads(threads)[0]

        with pytest.raises(Exception):
            signal.title = "Tampered"


# ==============================================================
# CALENDAR NORMALIZER TESTS
# ==============================================================

class TestCalendarNormalizer:

    def test_normalize_single_event(self):
        """normalize_calendar_events must convert one event into one UnifiedSignal."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [_calendar_event()]
        signals = normalize_calendar_events(events)

        assert len(signals) == 1
        assert signals[0].signal_type == "CALENDAR_EVENT"

    def test_normalize_extracts_event_title(self):
        """Signal title must match the event's 'summary' field."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [_calendar_event(summary="All Hands Meeting")]
        signals = normalize_calendar_events(events)

        assert signals[0].title == "All Hands Meeting"

    def test_normalize_parses_datetime(self):
        """Signal timestamp must be a timezone-aware UTC datetime."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [_calendar_event()]
        signals = normalize_calendar_events(events)

        assert signals[0].timestamp.tzinfo is not None
        assert signals[0].timestamp.tzinfo == timezone.utc

    def test_normalize_all_day_event(self):
        """Events with 'date' (not 'dateTime') must set is_all_day=True."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [{
            "id": "allday1",
            "summary": "Company Holiday",
            "start": {"date": "2026-05-01"},
            "end": {"date": "2026-05-02"},
        }]
        signals = normalize_calendar_events(events)

        assert signals[0].is_all_day is True

    def test_normalize_detects_missing_link(self):
        """Event without hangoutLink and with multiple attendees must flag requires_action."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [_calendar_event(has_link=False, attendee_count=3)]
        signals = normalize_calendar_events(events)

        assert signals[0].requires_action is True

    def test_normalize_event_without_start_is_skipped(self):
        """Calendar events missing 'start' must be skipped gracefully."""
        from daily_attention_agent.app.connectors.calendar.normalize import normalize_calendar_events

        events = [{"id": "bad", "summary": "No Start"}]
        signals = normalize_calendar_events(events)

        assert len(signals) == 0


# ==============================================================
# EMAIL RULES / SCORING TESTS
# ==============================================================

class TestEmailRules:

    def _make_signal(self, subject="Test", snippet="", sender="x@example.com", days_old=0):
        from daily_attention_agent.app.connectors.gmail.normalize import normalize_gmail_threads
        threads = [_gmail_thread(subject=subject, sender=sender, snippet=snippet, days_old=days_old)]
        return normalize_gmail_threads(threads)[0]

    def test_requires_action_adds_score(self):
        """Email that requires action must score higher than one that doesn't."""
        from daily_attention_agent.app.rules.email_rules import apply_email_rules

        action_signal = self._make_signal(subject="Please review this immediately?")
        passive_signal = self._make_signal(subject="FYI: Weekend schedule")

        action_score, _ = apply_email_rules(action_signal, [], [])
        passive_score, _ = apply_email_rules(passive_signal, [], [])

        assert action_score > passive_score

    def test_vip_sender_boosts_score(self):
        """Email from a VIP sender must score higher than one from unknown sender."""
        from daily_attention_agent.app.rules.email_rules import apply_email_rules

        vip_signal = self._make_signal(sender="ceo@bigcorp.com")
        normal_signal = self._make_signal(sender="someone@unknown.com")

        vip_score, _ = apply_email_rules(vip_signal, ["ceo@bigcorp.com"], [])
        normal_score, _ = apply_email_rules(normal_signal, [], [])

        assert vip_score > normal_score

    def test_keyword_match_boosts_score(self):
        """Email matching a user keyword must score higher than one without."""
        from daily_attention_agent.app.rules.email_rules import apply_email_rules

        keyword_signal = self._make_signal(subject="Project Alpha deadline approaching")
        no_keyword = self._make_signal(subject="Random update")

        kw_score, _ = apply_email_rules(keyword_signal, [], ["project alpha"])
        no_score, _ = apply_email_rules(no_keyword, [], ["project alpha"])

        assert kw_score > no_score

    def test_old_email_gets_staleness_boost(self):
        """Email older than 24 hours must receive a staleness score boost."""
        from daily_attention_agent.app.rules.email_rules import apply_email_rules

        old_signal = self._make_signal(days_old=2)
        fresh_signal = self._make_signal(days_old=0)

        old_score, _ = apply_email_rules(old_signal, [], [])
        fresh_score, _ = apply_email_rules(fresh_signal, [], [])

        assert old_score > fresh_score


# ==============================================================
# PRIORITY LEVEL FUNCTION TEST
# ==============================================================

class TestPriorityLevelFromScore:

    @pytest.mark.parametrize("score,expected_level", [
        (95, "critical"),
        (75, "high"),
        (55, "medium"),
        (35, "low"),
        (10, "low"),
    ])
    def test_score_maps_to_correct_level(self, score, expected_level):
        """priority_level_from_score must return the correct band for each score."""
        from daily_attention_agent.app.rules.scoring import priority_level_from_score
        assert priority_level_from_score(score) == expected_level
