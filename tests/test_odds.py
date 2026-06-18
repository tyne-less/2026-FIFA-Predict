import pytest

from betting.odds import decimal_to_implied_prob, no_vig_probabilities


def test_decimal_to_implied_prob():
    assert decimal_to_implied_prob(2.0) == 0.5


def test_decimal_to_implied_prob_rejects_invalid_odds():
    with pytest.raises(ValueError):
        decimal_to_implied_prob(1.0)


def test_no_vig_probabilities_sum_to_one():
    probabilities = no_vig_probabilities(2.0, 3.0, 4.0)

    assert probabilities["home"] == pytest.approx(6 / 13)
    assert probabilities["draw"] == pytest.approx(4 / 13)
    assert probabilities["away"] == pytest.approx(3 / 13)
    assert sum(probabilities.values()) == pytest.approx(1.0)
