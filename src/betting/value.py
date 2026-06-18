from pydantic import BaseModel, field_validator


class ProbabilityInput(BaseModel):
    probability: float

    @field_validator("probability")
    @classmethod
    def probability_must_be_valid(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("probability must be between 0 and 1")
        return value


class DecimalOddsInput(BaseModel):
    odds: float

    @field_validator("odds")
    @classmethod
    def odds_must_be_valid(cls, value: float) -> float:
        if value <= 1.0:
            raise ValueError("odds must be greater than 1.0")
        return value


def calculate_ev(model_prob: float, decimal_odds: float) -> float:
    ProbabilityInput(probability=model_prob)
    DecimalOddsInput(odds=decimal_odds)
    return model_prob * (decimal_odds - 1) - (1 - model_prob)


def calculate_edge(model_prob: float, market_prob: float) -> float:
    ProbabilityInput(probability=model_prob)
    ProbabilityInput(probability=market_prob)
    return model_prob - market_prob


def classify_risk(edge: float, ev: float) -> str:
    if ev <= 0:
        return "No value"
    if edge < 0.03:
        return "Small edge"
    if edge < 0.07:
        return "Medium edge"
    return "High edge / High uncertainty"
