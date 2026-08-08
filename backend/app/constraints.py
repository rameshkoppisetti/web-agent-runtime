from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FlightRequest:
    origin: str | None
    destination: str | None
    departure_date: str | None
    sort_by: str = "price"
    non_stop_only: bool = False

    @property
    def missing(self) -> list[str]:
        return [
            name
            for name, value in (
                ("origin", self.origin),
                ("destination", self.destination),
                ("departure date", self.departure_date),
            )
            if not value
        ]


def parse_flight_request(objective: str) -> FlightRequest | None:
    if not re.search(r"\b(flights?|fly|airfare)\b", objective, re.IGNORECASE):
        return None
    route = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\s+(?:on|for|leaving|departing)\b|$)", objective, re.IGNORECASE)
    date = re.search(
        r"\b(?:on|leaving|departing)\s+((?:\d{4}-\d{1,2}-\d{1,2})|(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:today|tomorrow)|(?:[A-Za-z]{3,9}\s+\d{1,2}(?:,?\s+\d{4})?))",
        objective,
        re.IGNORECASE,
    )
    lowered = objective.lower()
    sort_by = "duration" if any(term in lowered for term in ("shortest", "fastest", "least duration")) else "departure" if any(term in lowered for term in ("earliest", "morning")) else "price"
    return FlightRequest(
        origin=route.group(1).strip(" .,!") if route else None,
        destination=route.group(2).strip(" .,!") if route else None,
        departure_date=date.group(1) if date else None,
        sort_by=sort_by,
        non_stop_only=bool(re.search(r"\b(non[- ]?stop|direct)\b", objective, re.IGNORECASE)),
    )
