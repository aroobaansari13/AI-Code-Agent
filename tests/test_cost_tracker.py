
from decimal import Decimal

import pytest

from agent.cost_tracker import (
    CostTracker,
    BudgetExceededError,
)


def test_initial_budget():
    tracker = CostTracker()

    summary = tracker.get_summary()

    assert summary["budget_usd"] == 1.0
    assert summary["remaining_usd"] == 1.0
    assert summary["requests"] == 0


def test_cost_calculation():
    tracker = CostTracker()

    cost = tracker.calculate_cost(
        input_tokens=100000,
        output_tokens=50000,
    )

    assert cost == Decimal("0.330")


def test_record_usage():
    tracker = CostTracker()

    cost = tracker.record_usage(
        100000,
        50000,
    )

    assert cost == Decimal("0.330")

    summary = tracker.get_summary()

    assert summary["requests"] == 1
    assert summary["total_tokens"] == 150000
    assert summary["estimated_cost_usd"] == 0.33


def test_cumulative_usage():
    tracker = CostTracker()

    tracker.record_usage(
        100000,
        50000,
    )

    tracker.record_usage(
        100000,
        50000,
    )

    summary = tracker.get_summary()

    assert summary["requests"] == 2
    assert summary["total_tokens"] == 300000
    assert summary["estimated_cost_usd"] == 0.66


def test_can_afford_request():
    tracker = CostTracker()

    assert tracker.can_afford(
        100000,
        50000,
    )

    assert not tracker.can_afford(
        500000,
        200000,
    )


def test_budget_exceeded():
    tracker = CostTracker()

    with pytest.raises(BudgetExceededError):
        tracker.check_budget(
            500000,
            200000,
        )


def test_remaining_budget():
    tracker = CostTracker()

    tracker.record_usage(
        100000,
        50000,
    )

    summary = tracker.get_summary()

    assert summary["remaining_usd"] == 0.67


def test_reject_negative_tokens():
    tracker = CostTracker()

    with pytest.raises(ValueError):
        tracker.calculate_cost(
            -10,
            100,
        )


def test_reject_invalid_budget():
    with pytest.raises(ValueError):
        CostTracker(
            budget_usd="0",
        )


def test_record_usage_after_budget_exceeded():
    """
    Verify that actual API usage is recorded
    even when the configured budget is exceeded.
    """

    tracker = CostTracker()

    # The updated CostTracker records the usage
    # and then raises BudgetExceededError.
    with pytest.raises(BudgetExceededError):
        tracker.record_usage(
            500000,
            200000,
        )

    summary = tracker.get_summary()

    # Verify recorded token usage.
    assert summary["requests"] == 1
    assert summary["input_tokens"] == 500000
    assert summary["output_tokens"] == 200000
    assert summary["total_tokens"] == 700000

    # Verify budget exceeded status.
    assert summary["estimated_cost_usd"] > 1.00
    assert summary["budget_exceeded"] is True
    assert summary["remaining_usd"] == 0.0
