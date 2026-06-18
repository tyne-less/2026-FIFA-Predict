from display import format_edge, format_ev, format_probability, localize_risk


def test_format_probability():
    assert format_probability(0.455) == "45.5%"


def test_format_edge():
    assert format_edge(0.060) == "+6.0%"
    assert format_edge(-0.075) == "-7.5%"


def test_format_ev():
    assert format_ev(0.12) == "0.120"
    assert format_ev(-0.24) == "-0.240"
    assert format_ev(0.12, show_positive_sign=True) == "+0.120"


def test_localize_risk():
    assert localize_risk("No value") == "无明显价值"
    assert localize_risk("Small edge") == "小幅优势"
    assert localize_risk("Medium edge") == "中等优势"
    assert localize_risk("High edge / High uncertainty") == "高优势 / 高不确定性"
