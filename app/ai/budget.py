"""Conservative reservation with settlement even for malformed responses."""

from dataclasses import dataclass

from app.common.exceptions import AIProviderError


class AIBudgetExceeded(AIProviderError):
    pass


@dataclass
class TokenBudget:
    limit: int
    used: int = 0

    def reserve(self, amount: int) -> None:
        if self.used + amount > self.limit:
            raise AIBudgetExceeded("AI budget exhausted")
        self.used += amount

    def settle(self, reserved: int, usage: tuple[int, int] | None) -> None:
        if usage is not None:
            self.used += sum(usage) - reserved
