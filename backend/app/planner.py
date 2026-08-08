from __future__ import annotations

import json
import os
from dataclasses import dataclass


DEFAULT_PLAN = [
    "Parse the objective and establish safety constraints",
    "Open the starting page and inspect its state",
    "Collect a read-only result and report it",
]


@dataclass(frozen=True)
class Plan:
    steps: list[str]
    provider: str


class Planner:
    """Creates bounded, reviewable plans before any browser work begins."""

    def __init__(self) -> None:
        self.provider = os.getenv("MODEL_PROVIDER", "openai").lower()
        self.model = os.getenv("MODEL_NAME", "gpt-4.1-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def create(self, objective: str, start_url: str | None, max_steps: int) -> Plan:
        if self.provider == "openai" and self.api_key:
            try:
                return await self._openai_plan(objective, start_url, max_steps)
            except Exception:
                # A browser task remains runnable if a provider is temporarily unavailable.
                pass
        return Plan(steps=self._fallback_plan(objective)[:max_steps], provider="local fallback")

    async def _openai_plan(self, objective: str, start_url: str | None, max_steps: int) -> Plan:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        prompt = f"""Create a concise browser-agent plan for this objective: {objective!r}.
Starting URL: {start_url or 'not provided'}.
Return JSON only in the form {{\"steps\": [\"...\"]}}.
Use no more than {max_steps} steps. Actions must be read-only or reversible.
Never include checkout, purchase, booking confirmation, account changes, or sensitive-data entry."""
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You plan safe browser research tasks."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        steps = [str(step).strip() for step in parsed.get("steps", []) if str(step).strip()]
        if not steps:
            raise ValueError("Planner returned no steps")
        return Plan(steps=steps[:max_steps], provider=f"openai/{self.model}")

    @staticmethod
    def _fallback_plan(objective: str) -> list[str]:
        if "flight" in objective.lower():
            return [
                "Extract the requested route and travel constraints",
                "Open the travel site and inspect its flight-search controls",
                "Search only when all required trip details are present",
                "Collect a structured shortlist without booking or payment",
            ]
        return DEFAULT_PLAN.copy()
