from core.presets import PRESETS


def test_four_presets_present():
    assert set(PRESETS) == {"A", "B", "C", "fomo"}


def test_rr_values():
    assert PRESETS["A"].rr == 4.0
    assert PRESETS["C"].rr == 10.0 / 1.8


def test_sizing_and_leverage():
    assert PRESETS["A"].sizing == "fixed"
    assert PRESETS["B"].sizing == "percent"
    assert PRESETS["A"].leverage == 10.0
    assert PRESETS["fomo"].leverage == 1.0
    assert PRESETS["fomo"].fee_model == "spot"
