from pydantic import BaseModel, field_validator


class OddsInput(BaseModel):
    odds: float

    @field_validator("odds")
    @classmethod
    def odds_must_be_valid(cls, value: float) -> float:
        if value <= 1.0:
            raise ValueError("odds must be greater than 1.0")
        return value


def decimal_to_implied_prob(odds: float) -> float:
    OddsInput(odds=odds)
    return 1 / odds


def no_vig_probabilities(home_odds: float, draw_odds: float, away_odds: float) -> dict:
    implied = {
        "home": decimal_to_implied_prob(home_odds),
        "draw": decimal_to_implied_prob(draw_odds),
        "away": decimal_to_implied_prob(away_odds),
    }
    total = sum(implied.values())
    return {outcome: probability / total for outcome, probability in implied.items()}
