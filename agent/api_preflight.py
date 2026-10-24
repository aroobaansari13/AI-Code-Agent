
import os
from dataclasses import dataclass


class PreflightError(ValueError):
    """Raised when API configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class PreflightConfig:
    model: str
    max_output_tokens: int
    budget_usd: float
    estimated_input_tokens: int
    input_price_per_million: float
    output_price_per_million: float


def check_api_preflight(
    config: PreflightConfig,
    api_key: str | None = None,
) -> dict:
    """
    Validate API settings without making a network request.

    Pricing values must be reviewed against official pricing
    before real generation.
    """

    model = config.model.strip()

    if model != "deepseek-v4-pro":
        raise PreflightError(
            f"Unexpected model: {model!r}. "
            "Confirm the exact model ID before continuing."
        )

    key = api_key if api_key is not None else os.getenv(
        "DEEPSEEK_API_KEY", ""
    )

    if not key or not key.strip():
        raise PreflightError(
            "DEEPSEEK_API_KEY is missing."
        )

    if not isinstance(config.max_output_tokens, int):
        raise PreflightError(
            "max_output_tokens must be an integer."
        )

    if not 1 <= config.max_output_tokens <= 2000:
        raise PreflightError(
            "For the initial real test, max_output_tokens "
            "must be between 1 and 2000."
        )

    if config.estimated_input_tokens < 0:
        raise PreflightError(
            "Estimated input tokens cannot be negative."
        )

    if config.budget_usd <= 0:
        raise PreflightError(
            "Budget must be greater than zero."
        )

    if (
        config.input_price_per_million <= 0
        or config.output_price_per_million <= 0
    ):
        raise PreflightError(
            "Token prices must be positive."
        )

    estimated_request_cost = (
        config.estimated_input_tokens
        * config.input_price_per_million
        + config.max_output_tokens
        * config.output_price_per_million
    ) / 1_000_000

    if estimated_request_cost > config.budget_usd:
        raise PreflightError(
            "Estimated request cost exceeds the budget."
        )

    return {
        "passed": True,
        "model": model,
        "max_output_tokens": config.max_output_tokens,
        "estimated_request_cost_usd": round(
            estimated_request_cost, 6
        ),
        "budget_usd": config.budget_usd,
        "network_request_made": False,
    }
