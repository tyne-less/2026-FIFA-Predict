import pytest

from betting.value import calculate_edge, calculate_ev, classify_risk


def test_calculate_ev():
    assert calculate_ev(0.55, 2.0) == pytest.approx(0.1)


def test_calculate_edge():
    assert calculate_edge(0.55, 0.50) == pytest.approx(0.05)


def test_classify_risk():
    assert classify_risk(0.10, -0.01) == "No value"
    assert classify_risk(0.02, 0.01) == "Small edge"
    assert classify_risk(0.05, 0.01) == "Medium edge"
    assert classify_risk(0.07, 0.01) == "High edge / High uncertainty"
