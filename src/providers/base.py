from typing import Protocol


class OddsProvider(Protocol):
    def fetch_matches(self, date: str | None = None) -> list[dict]:
        ...

    def fetch_odds(self, match_id: str) -> dict | None:
        ...

    def fetch_all_odds(self, date: str | None = None) -> list[dict]:
        ...

