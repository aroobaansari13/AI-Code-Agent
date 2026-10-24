
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


class BudgetExceededError(Exception):
    """Raised when an API request exceeds the budget."""
    pass


class CostTracker:
    """Track estimated API costs across application runs."""

    def __init__(
        self,
        budget_usd="1.00",
        input_price="1.32",
        output_price="3.96",
        state_file=None,
    ):
        self.budget = self._valid_decimal(
            budget_usd,
            "Budget",
        )

        self.input_price = self._valid_decimal(
            input_price,
            "Input price",
        )

        self.output_price = self._valid_decimal(
            output_price,
            "Output price",
        )

        if self.budget <= 0:
            raise ValueError(
                "Budget must be positive."
            )

        if self.input_price < 0:
            raise ValueError(
                "Input price cannot be negative."
            )

        if self.output_price < 0:
            raise ValueError(
                "Output price cannot be negative."
            )

        self.state_file = (
            Path(state_file)
            if state_file is not None
            else None
        )

        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = Decimal("0")
        self.request_count = 0

        if (
            self.state_file is not None
            and self.state_file.exists()
        ):
            self.load_state()

    @staticmethod
    def _valid_decimal(value, name):
        """Convert a number to a finite Decimal."""

        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(
                f"{name} must be a valid number."
            ) from None

        if not result.is_finite():
            raise ValueError(
                f"{name} must be finite."
            )

        return result

    @staticmethod
    def _validate_tokens(
        input_tokens,
        output_tokens,
    ):
        """Validate token counts."""

        values = (
            input_tokens,
            output_tokens,
        )

        if any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in values
        ):
            raise ValueError(
                "Token counts must be "
                "non-negative integers."
            )

    def calculate_cost(
        self,
        input_tokens,
        output_tokens,
    ):
        """Estimate USD cost from token counts."""

        self._validate_tokens(
            input_tokens,
            output_tokens,
        )

        input_cost = (
            Decimal(input_tokens)
            * self.input_price
            / Decimal("1000000")
        )

        output_cost = (
            Decimal(output_tokens)
            * self.output_price
            / Decimal("1000000")
        )

        return input_cost + output_cost

    def get_remaining_budget(self):
        """Return remaining budget as Decimal."""

        return max(
            Decimal("0"),
            self.budget - self.total_cost,
        )

    def can_afford(
        self,
        input_tokens,
        output_tokens,
    ):
        """Check if planned request fits the budget."""

        estimated_cost = self.calculate_cost(
            input_tokens,
            output_tokens,
        )

        return (
            self.total_cost + estimated_cost
            <= self.budget
        )

    def check_budget(
        self,
        input_tokens,
        output_tokens,
    ):
        """Block requests exceeding remaining budget."""

        estimated_cost = self.calculate_cost(
            input_tokens,
            output_tokens,
        )

        if not self.can_afford(
            input_tokens,
            output_tokens,
        ):
            raise BudgetExceededError(
                "Estimated API request exceeds "
                "the remaining project budget. "
                f"Remaining: "
                f"${self.get_remaining_budget():.6f}; "
                f"Request estimate: "
                f"${estimated_cost:.6f}."
            )

    def record_usage(
        self,
        input_tokens,
        output_tokens,
    ):
        """Record usage returned by the API."""

        cost = self.calculate_cost(
            input_tokens,
            output_tokens,
        )

        # Record actual reported usage even if it exceeds
        # the configured budget. Never hide spending.
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_cost += cost
        self.request_count += 1

        self.save_state()

        if self.total_cost > self.budget:
            raise BudgetExceededError(
                "Recorded API usage exceeded "
                "the configured project budget."
            )

        return cost

    def save_state(self):
        """Persist usage locally using atomic replacement."""

        if self.state_file is None:
            return

        self.state_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost": str(self.total_cost),
            "request_count": self.request_count,
        }

        temporary_file = self.state_file.with_suffix(
            self.state_file.suffix + ".tmp"
        )

        temporary_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

        temporary_file.replace(
            self.state_file
        )

    def load_state(self):
        """Restore previously recorded usage."""

        data = json.loads(
            self.state_file.read_text(
                encoding="utf-8"
            )
        )

        input_tokens = data["input_tokens"]
        output_tokens = data["output_tokens"]
        request_count = data["request_count"]

        self._validate_tokens(
            input_tokens,
            output_tokens,
        )

        if (
            not isinstance(request_count, int)
            or isinstance(request_count, bool)
            or request_count < 0
        ):
            raise ValueError(
                "Invalid saved request count."
            )

        total_cost = self._valid_decimal(
            data["total_cost"],
            "Saved API cost",
        )

        if total_cost < 0:
            raise ValueError(
                "Invalid saved API cost."
            )

        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.request_count = request_count
        self.total_cost = total_cost

    def get_summary(self):
        """Return current project budget summary."""

        remaining = self.get_remaining_budget()

        return {
            "requests": self.request_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": (
                self.input_tokens
                + self.output_tokens
            ),
            "estimated_cost_usd": float(
                self.total_cost
            ),
            "budget_usd": float(
                self.budget
            ),
            "remaining_usd": float(
                remaining
            ),
            "budget_exceeded": (
                self.total_cost > self.budget
            ),
        }
