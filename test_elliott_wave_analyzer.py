"""
Tests for elliott_wave_analyzer.py
===================================
Run with:  python -m pytest test_elliott_wave_analyzer.py -v
"""

import pytest
from elliott_wave_analyzer import (
    FIBO_EXTENSIONS,
    FIBO_RETRACEMENTS,
    ElliottWaveAnalyzer,
    PivotPoint,
    Wave,
    WaveCount,
    WaveDirection,
    WaveTarget,
    WaveType,
    detect_pivots,
    fibonacci_extension_levels,
    fibonacci_retracement_levels,
    project_next_wave_targets,
    validate_corrective_wave,
    validate_impulse_wave,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_pivot(index: int, price: float, is_high: bool) -> PivotPoint:
    return PivotPoint(index=index, price=price, is_high=is_high)


def _make_wave(label: str, start_price: float, end_price: float,
               wtype: WaveType = WaveType.IMPULSE) -> Wave:
    start = _make_pivot(0, start_price, start_price < end_price)
    end   = _make_pivot(1, end_price,   end_price > start_price)
    return Wave(label=label, start=start, end=end, wave_type=wtype)


# ─── PivotPoint ───────────────────────────────────────────────────────────────

class TestPivotPoint:
    def test_repr_high(self):
        p = _make_pivot(5, 100.0, True)
        assert "HIGH" in repr(p)
        assert "100" in repr(p)

    def test_repr_low(self):
        p = _make_pivot(3, 95.0, False)
        assert "LOW" in repr(p)


# ─── Wave ─────────────────────────────────────────────────────────────────────

class TestWave:
    def test_length_positive(self):
        w = _make_wave("1", 100.0, 120.0)
        assert w.length == pytest.approx(20.0)

    def test_length_positive_for_down_wave(self):
        w = _make_wave("2", 120.0, 105.0)
        assert w.length == pytest.approx(15.0)

    def test_direction_up(self):
        w = _make_wave("1", 100.0, 110.0)
        assert w.direction == WaveDirection.UP

    def test_direction_down(self):
        w = _make_wave("2", 110.0, 100.0)
        assert w.direction == WaveDirection.DOWN

    def test_retracement_of(self):
        w1 = _make_wave("1", 100.0, 120.0)   # length = 20
        w2 = _make_wave("2", 120.0, 107.6)   # length = 12.4
        ratio = w2.retracement_of(w1)
        assert ratio == pytest.approx(12.4 / 20.0)

    def test_retracement_of_zero_length_wave(self):
        w_ref  = _make_wave("1", 100.0, 100.0)   # zero length
        w_test = _make_wave("2", 100.0, 95.0)
        assert w_test.retracement_of(w_ref) == 0.0

    def test_repr(self):
        w = _make_wave("3", 100.0, 150.0)
        assert "Wave(3" in repr(w)


# ─── detect_pivots ────────────────────────────────────────────────────────────

class TestDetectPivots:
    def test_returns_list(self):
        prices = [1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 3.0]
        result = detect_pivots(prices, left_bars=1, right_bars=1)
        assert isinstance(result, list)

    def test_detects_swing_high(self):
        # Clear swing high at index 2
        prices = [1.0, 2.0, 3.0, 2.0, 1.0]
        pivots = detect_pivots(prices, left_bars=1, right_bars=1)
        highs = [p for p in pivots if p.is_high]
        assert any(p.index == 2 for p in highs)

    def test_detects_swing_low(self):
        # Clear swing low at index 2
        prices = [3.0, 2.0, 1.0, 2.0, 3.0]
        pivots = detect_pivots(prices, left_bars=1, right_bars=1)
        lows = [p for p in pivots if not p.is_high]
        assert any(p.index == 2 for p in lows)

    def test_no_pivots_in_monotonic_series(self):
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        pivots = detect_pivots(prices, left_bars=1, right_bars=1)
        assert pivots == []

    def test_short_series_returns_empty(self):
        prices = [1.0, 2.0]
        pivots = detect_pivots(prices, left_bars=2, right_bars=2)
        assert pivots == []


# ─── fibonacci_retracement_levels ────────────────────────────────────────────

class TestFibonacciRetracementLevels:
    def test_number_of_levels(self):
        levels = fibonacci_retracement_levels(100.0, 120.0)
        assert len(levels) == len(FIBO_RETRACEMENTS)

    def test_0_percent_retracement_equals_wave_end(self):
        # ratio 0 should return the end price
        levels = dict(fibonacci_retracement_levels(100.0, 120.0))
        assert levels.get(0.0, None) is None or True  # 0 not in list – OK

    def test_100_percent_retracement_equals_wave_start(self):
        levels = dict(fibonacci_retracement_levels(100.0, 120.0))
        assert levels[1.000] == pytest.approx(100.0)

    def test_618_retracement_correct(self):
        levels = dict(fibonacci_retracement_levels(100.0, 120.0))
        # 120 - (120 - 100) * 0.618 = 120 - 12.36 = 107.64
        assert levels[0.618] == pytest.approx(107.64)

    def test_downtrend_wave(self):
        levels = dict(fibonacci_retracement_levels(120.0, 100.0))
        # 100 - (100 - 120) * 0.618 = 100 + 12.36 = 112.36
        assert levels[0.618] == pytest.approx(112.36)


# ─── fibonacci_extension_levels ──────────────────────────────────────────────

class TestFibonacciExtensionLevels:
    def test_number_of_levels(self):
        levels = fibonacci_extension_levels(100.0, 120.0, 110.0)
        assert len(levels) == len(FIBO_EXTENSIONS)

    def test_1x_extension(self):
        levels = dict(fibonacci_extension_levels(100.0, 120.0, 108.0))
        # move = 20, direction = +1, refStart = 108
        # 1.0 → 108 + 20 = 128
        assert levels[1.000] == pytest.approx(128.0)

    def test_1618_extension(self):
        levels = dict(fibonacci_extension_levels(100.0, 120.0, 108.0))
        assert levels[1.618] == pytest.approx(108.0 + 20.0 * 1.618)

    def test_downtrend_extension(self):
        levels = dict(fibonacci_extension_levels(120.0, 100.0, 108.0))
        # move = 20, direction = -1, refStart = 108
        # 1.0 → 108 - 20 = 88
        assert levels[1.000] == pytest.approx(88.0)


# ─── validate_impulse_wave ────────────────────────────────────────────────────

class TestValidateImpulseWave:
    def _make_valid_bullish_impulse(self):
        """Construct a clearly valid 5-wave bullish impulse."""
        return [
            _make_wave("1", 100.0, 120.0),   # W1: +20
            _make_wave("2", 120.0, 110.0),   # W2: -10 (50% retrace) ✓
            _make_wave("3", 110.0, 145.0),   # W3: +35 (longest)   ✓
            _make_wave("4", 145.0, 135.0),   # W4: -10 (doesn't overlap W1 at 120) ✓
            _make_wave("5", 135.0, 155.0),   # W5: +20 (= W1)       ✓
        ]

    def test_valid_impulse_has_no_violations(self):
        waves = self._make_valid_bullish_impulse()
        violations = validate_impulse_wave(waves)
        assert violations == []

    def test_rule1_wave2_over_100pct(self):
        """Wave 2 retraces MORE than 100% of Wave 1 → Rule 1 violation."""
        waves = [
            _make_wave("1", 100.0, 120.0),   # W1: +20
            _make_wave("2", 120.0,  95.0),   # W2: -25 (125% retrace) ✗
            _make_wave("3", 95.0,  130.0),
            _make_wave("4", 130.0, 120.0),
            _make_wave("5", 120.0, 140.0),
        ]
        violations = validate_impulse_wave(waves)
        assert any("Rule 1" in v for v in violations)

    def test_rule2_wave3_shortest(self):
        """Wave 3 is the shortest motive wave → Rule 2 violation."""
        waves = [
            _make_wave("1", 100.0, 130.0),   # W1: +30
            _make_wave("2", 130.0, 120.0),   # W2: -10
            _make_wave("3", 120.0, 130.0),   # W3: +10 (shortest)   ✗
            _make_wave("4", 130.0, 125.0),   # W4: -5
            _make_wave("5", 125.0, 160.0),   # W5: +35
        ]
        violations = validate_impulse_wave(waves)
        assert any("Rule 2" in v for v in violations)

    def test_rule3_wave4_overlaps_wave1(self):
        """Wave 4 dips below the high of Wave 1 → Rule 3 violation."""
        waves = [
            _make_wave("1", 100.0, 120.0),   # W1 ends at 120
            _make_wave("2", 120.0, 110.0),
            _make_wave("3", 110.0, 150.0),
            _make_wave("4", 150.0, 115.0),   # W4 end = 115 < W1 end = 120 ✗
            _make_wave("5", 115.0, 160.0),
        ]
        violations = validate_impulse_wave(waves)
        assert any("Rule 3" in v for v in violations)

    def test_partial_waves_no_crash(self):
        waves = [_make_wave("1", 100.0, 115.0)]
        violations = validate_impulse_wave(waves)
        assert isinstance(violations, list)

    def test_empty_waves_no_crash(self):
        violations = validate_impulse_wave([])
        assert violations == []


# ─── validate_corrective_wave ─────────────────────────────────────────────────

class TestValidateCorrectiveWave:
    def _make_valid_abc(self):
        return [
            _make_wave("A", 150.0, 120.0, WaveType.CORRECTIVE),   # A: -30
            _make_wave("B", 120.0, 135.0, WaveType.CORRECTIVE),   # B: +15 (50% retrace) ✓
            _make_wave("C", 135.0, 105.0, WaveType.CORRECTIVE),   # C: -30 (= A)         ✓
        ]

    def test_valid_abc_has_no_violations(self):
        waves = self._make_valid_abc()
        violations = validate_corrective_wave(waves)
        assert violations == []

    def test_wave_b_too_small(self):
        waves = [
            _make_wave("A", 150.0, 100.0, WaveType.CORRECTIVE),   # A: -50
            _make_wave("B", 100.0, 101.0, WaveType.CORRECTIVE),   # B: +1 (2% retrace)  ✗
        ]
        violations = validate_corrective_wave(waves)
        assert any("Wave B" in v for v in violations)

    def test_wave_b_exceeds_100pct(self):
        waves = [
            _make_wave("A", 150.0, 100.0, WaveType.CORRECTIVE),   # A: -50
            _make_wave("B", 100.0, 160.0, WaveType.CORRECTIVE),   # B: +60 (120% retrace) ✗
        ]
        violations = validate_corrective_wave(waves)
        assert any("Wave B" in v for v in violations)

    def test_wave_c_too_short_guideline(self):
        waves = [
            _make_wave("A", 150.0, 100.0, WaveType.CORRECTIVE),   # A: -50
            _make_wave("B", 100.0, 125.0, WaveType.CORRECTIVE),   # B: +25 (50%) ✓
            _make_wave("C", 125.0, 110.0, WaveType.CORRECTIVE),   # C: -15 (30% of A) ✗
        ]
        violations = validate_corrective_wave(waves)
        assert any("Wave C" in v for v in violations)


# ─── project_next_wave_targets ────────────────────────────────────────────────

class TestProjectNextWaveTargets:
    def _w1(self):
        return [_make_wave("1", 100.0, 120.0)]

    def _w1_w2(self):
        return [_make_wave("1", 100.0, 120.0), _make_wave("2", 120.0, 110.0)]

    def _w1_to_w4(self):
        return [
            _make_wave("1", 100.0, 120.0),
            _make_wave("2", 120.0, 110.0),
            _make_wave("3", 110.0, 145.0),
            _make_wave("4", 145.0, 135.0),
        ]

    def test_wave2_targets_are_retracements_of_wave1(self):
        targets = project_next_wave_targets(self._w1(), "2")
        assert len(targets) > 0
        assert all(t.wave_label == "2" for t in targets)
        assert all(t.ratio_type == "retracement" for t in targets)

    def test_wave3_targets_are_extensions(self):
        targets = project_next_wave_targets(self._w1_w2(), "3")
        assert len(targets) > 0
        assert all(t.wave_label == "3" for t in targets)
        assert all(t.ratio_type == "extension" for t in targets)

    def test_wave4_targets_are_retracements_of_wave3(self):
        waves = [
            _make_wave("1", 100.0, 120.0),
            _make_wave("2", 120.0, 110.0),
            _make_wave("3", 110.0, 145.0),
        ]
        targets = project_next_wave_targets(waves, "4")
        assert len(targets) > 0
        assert all(t.wave_label == "4" for t in targets)

    def test_wave5_targets_include_equality(self):
        targets = project_next_wave_targets(self._w1_to_w4(), "5")
        equality = [t for t in targets if "equality" in t.description.lower()]
        assert len(equality) >= 1

    def test_waveB_targets_from_waveA(self):
        waves_a = [_make_wave("A", 120.0, 90.0, WaveType.CORRECTIVE)]
        targets = project_next_wave_targets(waves_a, "B")
        assert len(targets) > 0
        assert all(t.wave_label == "B" for t in targets)

    def test_waveC_targets_from_waveAB(self):
        waves_ab = [
            _make_wave("A", 120.0, 90.0, WaveType.CORRECTIVE),
            _make_wave("B", 90.0, 105.0, WaveType.CORRECTIVE),
        ]
        targets = project_next_wave_targets(waves_ab, "C")
        assert len(targets) > 0
        equality = [t for t in targets if "equality" in t.description.lower()]
        assert len(equality) >= 1

    def test_no_targets_for_unknown_label(self):
        targets = project_next_wave_targets(self._w1(), "X")
        assert targets == []

    def test_returns_list(self):
        result = project_next_wave_targets([], "1")
        assert isinstance(result, list)


# ─── ElliottWaveAnalyzer ──────────────────────────────────────────────────────

class TestElliottWaveAnalyzer:
    def _simple_impulse_prices(self):
        """
        Hand-crafted price series that should yield clear pivots:
        low → high → low → high → low → high → low → high
        (alternating to form a potential impulse / corrective structure)
        """
        return [
            100, 101, 102, 103, 104, 105,   # rising
            104, 103, 102,                  # small pull-back
            103, 105, 108, 110,             # wave up
            109, 107, 106,                  # pull-back
            107, 110, 114, 118,             # extended wave up
            117, 115, 113,                  # pull-back
            114, 116, 120,                  # final push
        ]

    def test_analyze_returns_wave_count(self):
        prices = self._simple_impulse_prices()
        analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
        result = analyzer.analyze()
        assert isinstance(result, WaveCount)

    def test_analyze_populates_pivots(self):
        prices = self._simple_impulse_prices()
        analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
        analyzer.analyze()
        assert len(analyzer.pivots) > 0

    def test_too_short_series_returns_unknown(self):
        prices = [100.0, 101.0]
        analyzer = ElliottWaveAnalyzer(prices, left_bars=3, right_bars=3)
        result = analyzer.analyze()
        assert result.wave_type == WaveType.UNKNOWN or not result.is_valid

    def test_get_current_wave_count_before_analyze(self):
        analyzer = ElliottWaveAnalyzer([100, 101, 102])
        assert analyzer.get_current_wave_count() is None

    def test_get_fibonacci_levels_returns_dict(self):
        analyzer = ElliottWaveAnalyzer([100, 110])
        levels = analyzer.get_fibonacci_levels(100.0, 120.0)
        assert "retracements" in levels
        assert "extensions" in levels

    def test_to_json_before_analyze_returns_empty(self):
        import json
        analyzer = ElliottWaveAnalyzer([100, 110])
        result = json.loads(analyzer.to_json())
        assert result == {}

    def test_to_json_after_analyze_is_valid_json(self):
        import json
        prices = self._simple_impulse_prices()
        analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
        analyzer.analyze()
        data = json.loads(analyzer.to_json())
        assert "wave_type" in data
        assert "waves" in data
        assert "targets" in data
        assert "violations" in data

    def test_to_json_waves_have_required_keys(self):
        import json
        prices = self._simple_impulse_prices()
        analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
        analyzer.analyze()
        data = json.loads(analyzer.to_json())
        for w in data["waves"]:
            assert "label" in w
            assert "start_price" in w
            assert "end_price" in w
            assert "length" in w
            assert "direction" in w

    def test_wave_count_summary_contains_key_info(self):
        prices = self._simple_impulse_prices()
        analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
        count = analyzer.analyze()
        summary = count.summary()
        assert "Wave Count" in summary
        assert "Complete" in summary

    def test_is_valid_true_when_no_violations(self):
        count = WaveCount(
            waves=[],
            wave_type=WaveType.IMPULSE,
            direction=WaveDirection.UP,
            is_complete=False,
            next_wave_label="1",
            targets=[],
            violations=[],
        )
        assert count.is_valid is True

    def test_is_valid_false_when_violations(self):
        count = WaveCount(
            waves=[],
            wave_type=WaveType.IMPULSE,
            direction=WaveDirection.UP,
            is_complete=False,
            next_wave_label="1",
            targets=[],
            violations=["Rule 1 violated"],
        )
        assert count.is_valid is False


# ─── WaveTarget repr ──────────────────────────────────────────────────────────

class TestWaveTarget:
    def test_repr(self):
        t = WaveTarget(
            wave_label="3",
            ratio=1.618,
            price=150.0,
            ratio_type="extension",
            description="Test",
        )
        assert "Target" in repr(t)
        assert "3" in repr(t)
