"""Turn budget, agent tier enforcement, and cost limiting."""
import structlog

logger = structlog.get_logger()


class CostGovernor:
    def __init__(self, max_cost_usd: float = 15.0):
        self.max_cost_usd = max_cost_usd
        self.total_cost_usd: float = 0.0
        self._turn_costs: list[float] = []
        self._warnings_issued: int = 0

    def record_turn_cost(self, cost_usd: float) -> None:
        self.total_cost_usd = round(self.total_cost_usd + cost_usd, 6)
        self._turn_costs.append(cost_usd)

        if self.total_cost_usd > self.max_cost_usd * 0.8 and self._warnings_issued == 0:
            logger.warning(
                "cost_approaching_limit",
                current=self.total_cost_usd,
                limit=self.max_cost_usd,
            )
            self._warnings_issued += 1

    def is_over_limit(self) -> bool:
        return self.total_cost_usd >= self.max_cost_usd

    def remaining_budget(self) -> float:
        return max(0.0, self.max_cost_usd - self.total_cost_usd)

    def avg_turn_cost(self) -> float:
        if not self._turn_costs:
            return 0.0
        return round(sum(self._turn_costs) / len(self._turn_costs), 6)

    def estimated_turns_remaining(self) -> int:
        avg = self.avg_turn_cost()
        if avg <= 0:
            return 999
        return int(self.remaining_budget() / avg)
