"""God's-eye variable injection for simulation scenarios.
Allows founders to inject market shocks, competitor moves, or other
variables at specific turns during the simulation."""
import structlog

logger = structlog.get_logger()


class VariableInjector:
    def __init__(self, assumptions: dict):
        self.assumptions = assumptions
        self.scheduled_injections: list[dict] = []
        self._applied: list[dict] = []

    def schedule(self, turn: int, variable: str, value: str, description: str = "") -> None:
        self.scheduled_injections.append({
            "turn": turn,
            "variable": variable,
            "value": value,
            "description": description,
        })
        self.scheduled_injections.sort(key=lambda x: x["turn"])

    def get_injections_for_turn(self, turn: int) -> list[dict]:
        injections = [inj for inj in self.scheduled_injections if inj["turn"] == turn]
        for inj in injections:
            self._applied.append(inj)
            logger.info(
                "variable_injected",
                turn=turn,
                variable=inj["variable"],
                value=inj["value"],
            )
        return injections

    def build_context_modifier(self, turn: int) -> str:
        injections = self.get_injections_for_turn(turn)
        if not injections:
            return ""

        lines = ["MARKET UPDATE:"]
        for inj in injections:
            desc = inj.get("description", f"{inj['variable']} changed to {inj['value']}")
            lines.append(f"- {desc}")
        return "\n".join(lines)

    @staticmethod
    def from_assumptions(assumptions: list[dict]) -> "VariableInjector":
        injector = VariableInjector({})
        for assumption in assumptions:
            var = assumption.get("variable", "")
            val = assumption.get("value", "")
            injector.assumptions[var] = val
        return injector
