from betting.handicap import (
    format_handicap_line,
    format_handicap_result_label,
    get_handicap_result,
)


def test_handicap_result_with_home_giving_one_goal():
    assert get_handicap_result(2, 1, -1) == "handicap_draw"
    assert get_handicap_result(3, 1, -1) == "handicap_home"


def test_handicap_result_with_home_receiving_one_goal():
    assert get_handicap_result(1, 1, 1) == "handicap_home"
    assert get_handicap_result(0, 1, 1) == "handicap_draw"


def test_handicap_labels_format_correctly():
    assert format_handicap_result_label("Japan", "Tunisia", -1, "handicap_home") == "让胜"
    assert format_handicap_result_label("Japan", "Tunisia", -1, "handicap_draw") == "让平"
    assert format_handicap_result_label("Japan", "Tunisia", -1, "handicap_away") == "让负"
    assert format_handicap_line("Japan", -1) == "Japan -1"
    assert format_handicap_line("Japan", 1) == "Japan +1"
    assert format_handicap_line("Japan", 0) == "Japan 0"
