
import pytest

from agent.api_preflight import (
    PreflightConfig,
    PreflightError,
    check_api_preflight,
)


def make_config(**overrides):
    values = {
        "model": "deepseek-v4-pro",
        "max_output_tokens": 2000,
        "budget_usd": 1.00,
        "estimated_input_tokens": 10000,
        "input_price_per_million": 1.32,
        "output_price_per_million": 3.96,
    }

    values.update(overrides)

    return PreflightConfig(**values)


def test_valid_configuration():
    result = check_api_preflight(
        make_config(),
        api_key="test-key",
    )

    assert result["passed"] is True
    assert result["network_request_made"] is False


def test_missing_api_key():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(),
            api_key="",
        )


def test_wrong_model():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(model="wrong-model"),
            api_key="test-key",
        )


def test_output_limit():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(max_output_tokens=5000),
            api_key="test-key",
        )


def test_budget_exceeded():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(
                budget_usd=0.001,
                estimated_input_tokens=100000,
            ),
            api_key="test-key",
        )


def test_negative_input_tokens():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(estimated_input_tokens=-1),
            api_key="test-key",
        )


def test_invalid_pricing():
    with pytest.raises(PreflightError):
        check_api_preflight(
            make_config(output_price_per_million=0),
            api_key="test-key",
        )


def test_estimated_cost():
    result = check_api_preflight(
        make_config(),
        api_key="test-key",
    )

    assert result["estimated_request_cost_usd"] == pytest.approx(
        0.02112
    )
