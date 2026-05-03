"""
Unit Tests: DAA Calendar Rules and Guardrails
Tests conflict detection, overload detection, schema validation, and no-side-effects guard.

Run with: pytest test_daa_rules_guardrails.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


# ==============================================================
# HELPER: Build calendar UnifiedSignal directly
# ==============================================================

def _cal_signal(title="Meeting", start_offset_hours=1, duration_hours=1,
                attendee_count=2, has_link=True, description="Agenda here",
                is_all_day=False, record_id=None, fixed_now=None):
    """Directly build a calendar UnifiedSignal without going through normalizer."""
    from daily_attention_agent.app.models.unified_signal import UnifiedSignal

    now = fixed_now or datetime.now(timezone.utc)
    start = now + timedelta(hours=start_offset_hours)
    end = start + timedelta(hours=duration_hours)
    record_id = record_id or f"evt_{title.replace(' ', '_')}"

    return UnifiedSignal(
        signal_type="CALENDAR_EVENT",
        source_tool="calendar",
        record_id=record_id,
        title=title,
        snippet=description or "No description provided",
        timestamp=start,
        end_time=end,
        is_all_day=is_all_day,
        requires_action=not has_link and attendee_count > 1,
        raw_metadata={
            "attendee_count": attendee_count,
            "has_meet_link": has_link,
            "is_all_day": is_all_day,
            "calendar_name": "primary",
        }
    )


# ==============================================================
# CALENDAR CONFLICT DETECTION TESTS
# ==============================================================

class TestDetectConflicts:

    def test_overlapping_events_detected(self):
        """Two events that overlap in time must be detected as conflicts."""
        from daily_attention_agent.app.rules.calendar_rules import detect_conflicts

        now = datetime.now(timezone.utc)
        # Event A: 10:00–11:00
        a = _cal_signal("Meeting A", start_offset_hours=1, duration_hours=1)
        # Event B: 10:30–11:30 (overlaps with A)
        b = _cal_signal("Meeting B", start_offset_hours=1.5, duration_hours=1)

        risks = detect_conflicts([a, b])
        assert len(risks) > 0
        assert "Meeting A" in risks[0]["events"] or "Meeting B" in risks[0]["events"]

    def test_non_overlapping_events_no_conflict(self):
        """Events that do not overlap must not produce any conflicts."""
        from daily_attention_agent.app.rules.calendar_rules import detect_conflicts

        a = _cal_signal("Morning Meeting", start_offset_hours=1, duration_hours=1)
        b = _cal_signal("Afternoon Meeting", start_offset_hours=3, duration_hours=1)

        risks = detect_conflicts([a, b])
        assert risks == []

    def test_all_day_events_ignored_for_conflict(self):
        """All-day events must not be included in conflict detection."""
        from daily_attention_agent.app.rules.calendar_rules import detect_conflicts

        all_day = _cal_signal("Holiday", is_all_day=True)
        regular = _cal_signal("Regular Meeting", start_offset_hours=2)

        risks = detect_conflicts([all_day, regular])
        # All-day events should be skipped
        assert risks == []

    def test_empty_event_list_no_conflicts(self):
        """Empty calendar must return no conflicts."""
        from daily_attention_agent.app.rules.calendar_rules import detect_conflicts
        assert detect_conflicts([]) == []


# ==============================================================
# OVERLOAD DETECTION TESTS
# ==============================================================

class TestDetectOverload:

    def test_many_hours_triggers_overload(self):
        """More than 5 hours of meetings in one day must trigger overload risk."""
        from daily_attention_agent.app.rules.calendar_rules import detect_overload

        # Create 6 x 1-hour meetings spread through the day
        signals = [_cal_signal(f"Meeting {i}", start_offset_hours=i, duration_hours=1)
                   for i in range(6)]

        risks = detect_overload(signals)
        assert len(risks) > 0
        assert "overload" in risks[0]["title"].lower()

    def test_few_hours_no_overload(self):
        """Less than 5 hours of meetings must not trigger overload."""
        from daily_attention_agent.app.rules.calendar_rules import detect_overload

        signals = [_cal_signal(f"Meeting {i}", start_offset_hours=i, duration_hours=0.5)
                   for i in range(2)]  # Only 1 hour total

        risks = detect_overload(signals)
        assert risks == []

    def test_all_day_events_excluded_from_hours(self):
        """All-day events must not be counted toward meeting hours."""
        from daily_attention_agent.app.rules.calendar_rules import detect_overload

        all_days = [_cal_signal("Holiday", is_all_day=True) for _ in range(10)]
        risks = detect_overload(all_days)
        assert risks == []


# ==============================================================
# MISSING LINKS DETECTION
# ==============================================================

class TestDetectMissingLinks:

    def test_meeting_without_link_flagged(self):
        """A multi-person meeting with no join link must be flagged."""
        from daily_attention_agent.app.rules.calendar_rules import detect_missing_links

        event = _cal_signal("Team Review", has_link=False, attendee_count=4)
        risks = detect_missing_links([event])

        assert len(risks) > 0
        assert "Team Review" in risks[0]["events"]

    def test_solo_meeting_without_link_not_flagged(self):
        """A single-person event (no other attendees) without a link should not be flagged."""
        from daily_attention_agent.app.rules.calendar_rules import detect_missing_links

        event = _cal_signal("Solo Focus Time", has_link=False, attendee_count=1)
        risks = detect_missing_links([event])

        assert risks == []

    def test_meeting_with_link_not_flagged(self):
        """Event with a join link must not be flagged even with multiple attendees."""
        from daily_attention_agent.app.rules.calendar_rules import detect_missing_links

        event = _cal_signal("Team Call", has_link=True, attendee_count=5)
        risks = detect_missing_links([event])

        assert risks == []


# ==============================================================
# DUPLICATE DETECTION TESTS
# ==============================================================

class TestDetectDuplicates:

    def test_duplicate_events_detected(self):
        """Two events with the same title and timestamp must be detected as duplicates."""
        from daily_attention_agent.app.rules.calendar_rules import detect_duplicates

        now = datetime.now(timezone.utc)
        a = _cal_signal("Standup", start_offset_hours=1, record_id="e1", fixed_now=now)
        b = _cal_signal("Standup", start_offset_hours=1, record_id="e2", fixed_now=now)

        risks = detect_duplicates([a, b])
        assert len(risks) > 0

    def test_no_duplicates_when_unique(self):
        """Unique events must not produce any duplicate risks."""
        from daily_attention_agent.app.rules.calendar_rules import detect_duplicates

        a = _cal_signal("Morning Standup", start_offset_hours=1)
        b = _cal_signal("Afternoon Review", start_offset_hours=5)

        risks = detect_duplicates([a, b])
        assert risks == []


# ==============================================================
# GUARDRAIL: SCHEMA VALIDATION
# ==============================================================

class TestValidateSchema:

    def _make_state_with_items(self, items):
        """Build a minimal DAAState with attention_items."""
        from daily_attention_agent.app.core.state import DAAState
        from datetime import timezone

        state = DAAState(
            user_id="u1", workspace_id="w1",
            time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        )
        state.attention_items = items
        state.risks = []
        state.opportunities = []
        return state

    def test_valid_state_passes_schema(self):
        """A properly structured state must pass schema validation without error."""
        from daily_attention_agent.app.guardrails.validate_schema import validate_schema

        items = [{
            "title": "Test Item",
            "priority_score": 75.0,
            "priority_level": "high",
            "recommended_action": "Review and respond",
            "evidence": {"tool": "gmail", "record_id": "r1", "timestamp": datetime.now(timezone.utc).isoformat(), "snippet": "Test"},
            "confidence": 0.9,
        }]
        state = self._make_state_with_items(items)
        validate_schema(state)  # must not raise

    def test_missing_title_fails_schema(self):
        """AttentionItem without 'title' must raise AssertionError."""
        from daily_attention_agent.app.guardrails.validate_schema import validate_schema

        items = [{"priority_score": 75.0, "priority_level": "high",
                  "recommended_action": "Review", "evidence": {}, "confidence": 0.9}]
        state = self._make_state_with_items(items)

        with pytest.raises(AssertionError):
            validate_schema(state)

    def test_empty_attention_items_passes(self):
        """Empty attention_items list must pass schema validation."""
        from daily_attention_agent.app.guardrails.validate_schema import validate_schema

        state = self._make_state_with_items([])
        validate_schema(state)  # must not raise


# ==============================================================
# GUARDRAIL: NO SIDE EFFECTS
# ==============================================================

class TestValidateNoSideEffects:

    def _make_state(self, attention_items=None, drafts=None):
        from daily_attention_agent.app.core.state import DAAState
        state = DAAState(
            user_id="u1", workspace_id="w1",
            time_window={"start": datetime.now(timezone.utc), "end": datetime.now(timezone.utc)},
        )
        state.attention_items = attention_items or []
        state.drafts = drafts or []
        return state

    def test_passive_action_passes(self):
        """'Review and respond if needed' must pass the no-side-effects check."""
        from daily_attention_agent.app.guardrails.no_side_effects import validate_no_side_effects

        state = self._make_state(attention_items=[{"recommended_action": "Review and respond if needed"}])
        validate_no_side_effects(state)  # must not raise

    def test_forbidden_word_sent_raises(self):
        """'sent' in recommended_action must raise AssertionError."""
        from daily_attention_agent.app.guardrails.no_side_effects import validate_no_side_effects

        state = self._make_state(attention_items=[{"recommended_action": "Email sent to the team"}])
        with pytest.raises(AssertionError):
            validate_no_side_effects(state)

    @pytest.mark.parametrize("action", [
        "Rescheduled the meeting",
        "Deleted old events",
        "Updated calendar entry",
        "Created new task",
    ])
    def test_all_forbidden_words_fail(self, action):
        """All forbidden action words must trigger AssertionError."""
        from daily_attention_agent.app.guardrails.no_side_effects import validate_no_side_effects

        state = self._make_state(attention_items=[{"recommended_action": action}])
        with pytest.raises(AssertionError):
            validate_no_side_effects(state)

    def test_draft_without_is_draft_flag_fails(self):
        """Draft without is_draft=True must raise AssertionError."""
        from daily_attention_agent.app.guardrails.no_side_effects import validate_no_side_effects

        state = self._make_state(drafts=[{"subject": "Test", "body": "Hello", "is_draft": False}])
        with pytest.raises(AssertionError):
            validate_no_side_effects(state)
