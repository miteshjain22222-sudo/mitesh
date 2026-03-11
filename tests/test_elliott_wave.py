"""Tests for the elliott_wave package.

Covers all major rules and patterns described in
SweeGlu Practical Application of Elliott Wave Principle.
"""

import pytest
from elliott_wave.fibonacci import (
    retracement_price,
    retracement_ratio,
    projection_price,
    wave_length,
    retracement_levels_for,
    projection_levels_for,
    RATIO_38,
    RATIO_61,
    RATIO_100,
    RATIO_161,
)
from elliott_wave.rules import (
    check_wave2_retrace,
    check_wave3_not_shortest,
    check_wave4_no_overlap,
    check_wave5_qualification,
    check_38pct_breakout,
    alternation_check,
    check_impulse_wave,
    classify_wave3,
    classify_wave5,
)
from elliott_wave.patterns import (
    PatternType,
    detect_impulse,
    detect_leading_diagonal,
    detect_ending_diagonal,
    detect_zigzag,
    detect_irregular_correction,
    detect_flat_correction,
    detect_complex_correction,
    zigzag_trade_setup,
)
from elliott_wave.analyzer import ElliottWaveAnalyzer


# ── Fibonacci utilities ──────────────────────────────────────────────────────

class TestFibonacci:
    def test_retracement_price_38pct(self):
        # Wave from 100 to 200; 38.2% retracement should be 200 - 38.2 = 161.8
        assert retracement_price(100, 200, RATIO_38) == pytest.approx(161.8, rel=1e-3)

    def test_retracement_price_61pct(self):
        assert retracement_price(100, 200, RATIO_61) == pytest.approx(138.2, rel=1e-3)

    def test_retracement_price_bearish(self):
        # Bear wave from 200 down to 100; 38.2% retrace up = 100 + 38.2 = 138.2
        assert retracement_price(200, 100, RATIO_38) == pytest.approx(138.2, rel=1e-3)

    def test_retracement_ratio_calculation(self):
        ratio = retracement_ratio(100, 200, 161.8)
        assert ratio == pytest.approx(RATIO_38, rel=1e-2)

    def test_retracement_ratio_zero_wave_raises(self):
        with pytest.raises(ValueError):
            retracement_ratio(100, 100, 100)

    def test_projection_price_100pct(self):
        # Wave 1 from 100→150 (length 50), project 100% from 130 → 130+50=180
        assert projection_price(100, 150, 130, RATIO_100) == pytest.approx(180.0)

    def test_wave_length(self):
        assert wave_length(100, 200) == 100.0
        assert wave_length(200, 100) == 100.0

    def test_retracement_levels_keys(self):
        levels = retracement_levels_for(100, 200)
        assert "38.2%" in levels
        assert "61.8%" in levels
        assert "100.0%" in levels

    def test_projection_levels_keys(self):
        levels = projection_levels_for(100, 200, 150)
        assert "161.8%" in levels
        assert "38.2%" in levels


# ── Chapter 1 – Basic Rules ──────────────────────────────────────────────────

class TestBasicRules:
    # Wave 2 Retracement Rule
    def test_wave2_valid_retrace(self):
        # Wave 1: 100→200; Wave 2 ends at 150 (50% retrace – valid)
        result = check_wave2_retrace(100, 200, 150)
        assert result.passed

    def test_wave2_exactly_100pct_retrace(self):
        # Wave 2 ends exactly at Wave 1 start – invalid (must be strictly above)
        result = check_wave2_retrace(100, 200, 100)
        assert not result.passed

    def test_wave2_exceeds_100pct(self):
        # Wave 2 end goes below Wave 1 start
        result = check_wave2_retrace(100, 200, 90)
        assert not result.passed

    def test_wave2_bearish_valid(self):
        # Bear wave: Wave 1 from 200→100; Wave 2 ends at 140 (60% retrace – valid)
        result = check_wave2_retrace(200, 100, 140)
        assert result.passed

    def test_wave2_bearish_exceeds_100pct(self):
        # Bear wave: Wave 2 goes above Wave 1 start (210)
        result = check_wave2_retrace(200, 100, 210)
        assert not result.passed

    # Wave 3 Not Shortest Rule
    def test_wave3_not_shortest_valid(self):
        result = check_wave3_not_shortest(100, 150, 130, 210, 180, 230)
        assert result.passed

    def test_wave3_is_shortest_invalid(self):
        # W1 length=50, W3 length=20 (shortest), W5 length=40 → invalid
        result = check_wave3_not_shortest(100, 150, 140, 160, 145, 185)
        assert not result.passed

    # Wave 4 No Overlap Rule
    def test_wave4_no_overlap_valid(self):
        result = check_wave4_no_overlap(wave1_end=150, wave4_end=155, bullish=True)
        assert result.passed

    def test_wave4_overlaps_wave1(self):
        result = check_wave4_no_overlap(wave1_end=150, wave4_end=145, bullish=True)
        assert not result.passed

    def test_wave4_overlap_diagonal_exception(self):
        # Overlap is allowed in diagonal patterns
        result = check_wave4_no_overlap(
            wave1_end=150, wave4_end=145, bullish=True, is_diagonal=True
        )
        assert result.passed


# ── Chapter 4 – Wave Personalities ──────────────────────────────────────────

class TestWavePersonalities:
    def test_wave3_normal(self):
        # W3 length = 80 (W1 = 50) → 160%, just below 161.8%
        result = classify_wave3(100, 150, 130, 210)
        assert result.passed
        assert "Normal" in result.reason

    def test_wave3_extended(self):
        # W3 length = 120 vs W1 = 50 → 240% → extended
        result = classify_wave3(100, 150, 130, 250)
        assert result.passed
        assert "Extended" in result.reason

    def test_wave5_normal(self):
        # W5 length=42, W3 length=80, W1 length=40 → W5>W1, ratio=52.5%<61.8% → Normal
        result = classify_wave5(130, 210, 180, 222, 100, 140)
        assert result.passed
        assert "Normal" in result.reason

    def test_wave5_extended(self):
        # W5 length 60, W3 length 80 → 75% > 61.8% → extended
        result = classify_wave5(130, 210, 180, 240, 100, 150)
        assert result.passed
        assert "Extended" in result.reason

    def test_wave5_failure(self):
        # W5 length 10, W1 length 50 → failure
        result = classify_wave5(130, 210, 180, 190, 100, 150)
        assert not result.passed
        assert "Failed" in result.reason


# ── Chapters 7-9 – Impulse Pattern ───────────────────────────────────────────

class TestImpulsePattern:
    # A clean bullish impulse: W1=70, W3=128, W5=75 (W5>W1, W3 not shortest)
    # [W0, W1, W2, W3, W4, W5]
    PIVOTS = [0.0, 70.0, 42.0, 170.0, 125.0, 200.0]

    def test_valid_impulse(self):
        result = detect_impulse(self.PIVOTS, bullish=True)
        assert result.pattern == PatternType.IMPULSE
        assert result.passed

    def test_impulse_wrong_pivot_count(self):
        result = detect_impulse([0, 100, 60], bullish=True)
        assert not result.passed

    def test_wave5_targets_generated(self):
        result = detect_impulse(self.PIVOTS, bullish=True)
        assert result.passed
        assert "Wave5_38.2%" in result.targets

    def test_invalid_impulse_wave2_exceeds(self):
        # Wave 2 dips below Wave 0 start
        bad_pivots = [0.0, 100.0, -10.0, 180.0, 120.0, 200.0]
        result = detect_impulse(bad_pivots, bullish=True)
        assert not result.passed

    def test_leading_diagonal_overlap(self):
        # Wave 4 overlaps Wave 1 in a Leading Diagonal
        ld_pivots = [0.0, 80.0, 60.0, 150.0, 70.0, 200.0]
        result = detect_leading_diagonal(ld_pivots, bullish=True)
        assert result.pattern == PatternType.LEADING_DIAGONAL
        assert result.passed

    def test_ending_diagonal_overlap(self):
        ed_pivots = [0.0, 80.0, 60.0, 150.0, 70.0, 200.0]
        result = detect_ending_diagonal(ed_pivots, bullish=True)
        assert result.pattern == PatternType.ENDING_DIAGONAL
        assert result.passed


# ── Chapters 10-13 – Corrective Patterns ─────────────────────────────────────

class TestCorrectivePatterns:
    def test_simple_zigzag_valid(self):
        # Wave A: 200→150 (down 50), Wave B: 150→172 (44% retrace up, in 38-61% range),
        # Wave C: 172→110 (projects 124% of A – more than 100%)
        result = detect_zigzag(200, 150, 172, 110, bullish=False)
        assert result.pattern == PatternType.ZIGZAG
        assert result.passed

    def test_simple_zigzag_b_too_deep(self):
        # Wave B retraces 80% – outside 38-61% range
        result = detect_zigzag(200, 150, 110, 90, bullish=False)
        assert not result.passed

    def test_simple_zigzag_c_too_short(self):
        # Wave C projects only 80% of Wave A
        result = detect_zigzag(200, 150, 169.1, 155, bullish=False)
        assert not result.passed

    def test_irregular_correction_b_exceeds_100pct(self):
        # Wave A: 200→150, Wave B exceeds 100% → back above 200 to 210
        result = detect_irregular_correction(200, 150, 210, 130, bullish=False)
        assert result.pattern == PatternType.IRREGULAR_CORRECTION
        assert result.passed

    def test_irregular_correction_b_does_not_exceed(self):
        result = detect_irregular_correction(200, 150, 170, 130, bullish=False)
        assert not result.passed

    def test_flat_correction_valid(self):
        # Wave A: 200→150 (down 50), Wave B: 150→199 (98% retrace ≈ 100%),
        # Wave C: 199→155 (88% of Wave A – less than 100%)
        result = detect_flat_correction(200, 150, 199, 155)
        assert result.pattern == PatternType.FLAT
        assert result.passed

    def test_flat_correction_c_too_long(self):
        # Wave C more than 100% of Wave A – not a flat
        result = detect_flat_correction(200, 150, 149.5, 90)
        assert not result.passed

    def test_complex_correction_5_or_more_waves(self):
        result = detect_complex_correction(6)
        assert result.pattern == PatternType.COMPLEX_CORRECTION
        assert result.passed

    def test_complex_correction_too_few_waves(self):
        result = detect_complex_correction(3)
        assert not result.passed


# ── Chapter 14 – Wave 5 Qualification ────────────────────────────────────────

class TestWave5Qualification:
    def test_wave5_qualifies(self):
        # W3 end=180, W4 end=150, W5 end=200 (beyond W3 and >38% projection)
        result = check_wave5_qualification(180, 150, 200, bullish=True)
        assert result.passed

    def test_wave5_not_beyond_wave3(self):
        # W5 end below W3 end (170 < 180)
        result = check_wave5_qualification(180, 150, 170, bullish=True)
        assert not result.passed

    def test_wave5_minimum_projection_not_met(self):
        # W3 end=180, W4 end=150; 38% of (180-150)=30 → min proj=11.4
        # W5 end=151 → len5=1 < 11.4 → fail
        result = check_wave5_qualification(180, 150, 151, bullish=True)
        assert not result.passed


# ── Chapter 18 – 38% Breakout Logic ──────────────────────────────────────────

class TestBreakoutLogic:
    def test_38pct_breakout_confirmed_bullish(self):
        # Wave high=200, low=100; 38% retrace = 162. Price at 165 → above 162.
        result = check_38pct_breakout(100, 200, 165, bullish=True)
        assert result.passed

    def test_38pct_breakout_broken_bullish(self):
        # Price at 155 → below 38% level (162)
        result = check_38pct_breakout(100, 200, 155, bullish=True)
        assert not result.passed

    def test_38pct_breakout_bearish(self):
        # Wave high=200, low=100 (bear); 38% retrace up = 138. Price 130 → valid bear.
        result = check_38pct_breakout(200, 100, 130, bullish=False)
        assert result.passed

    def test_alternation_holds(self):
        # Wave 2 deep (70%), Wave 4 shallow (30%) → alternation holds
        result = alternation_check(0.70, 0.30)
        assert result.passed

    def test_alternation_not_observed(self):
        # Both corrections deep → alternation NOT observed
        result = alternation_check(0.70, 0.65)
        assert not result.passed


# ── Chapter 17-18 – Trade Setup ──────────────────────────────────────────────

class TestTradeSetup:
    def test_zigzag_trade_setup_keys(self):
        setup = zigzag_trade_setup(200, 150, 172, 110, bullish=False)
        assert "entry_zone" in setup
        assert "stop_loss" in setup
        assert "target_1" in setup
        assert "target_2" in setup

    def test_target_1_is_b_start(self):
        # Target 1 should be start of Wave C = b_end
        setup = zigzag_trade_setup(200, 150, 172, 110, bullish=False)
        assert setup["target_1"] == pytest.approx(172)

    def test_target_2_is_a_start(self):
        # Target 2 should be start of Wave A = a_start
        setup = zigzag_trade_setup(200, 150, 172, 110, bullish=False)
        assert setup["target_2"] == pytest.approx(200)


# ── Analyzer integration tests ────────────────────────────────────────────────

class TestElliottWaveAnalyzer:
    # W1=70, W3=128, W5=75 (W5>W1, W3 not shortest, W4 no overlap)
    IMPULSE_PIVOTS = [0.0, 70.0, 42.0, 170.0, 125.0, 200.0]

    def test_full_report_impulse(self):
        analyzer = ElliottWaveAnalyzer(self.IMPULSE_PIVOTS, bullish=True)
        report = analyzer.full_report()
        assert report.pattern == PatternType.IMPULSE
        assert report.valid

    def test_analyze_impulse_raises_with_too_few_pivots(self):
        analyzer = ElliottWaveAnalyzer([0, 100, 60], bullish=True)
        with pytest.raises(ValueError):
            analyzer.analyze_impulse()

    def test_analyze_correction_raises_with_too_few_pivots(self):
        analyzer = ElliottWaveAnalyzer([200, 150], bullish=False)
        with pytest.raises(ValueError):
            analyzer.analyze_correction()

    def test_current_wave_context(self):
        analyzer = ElliottWaveAnalyzer(self.IMPULSE_PIVOTS, bullish=True)
        ctx = analyzer.current_wave_context(175.0)
        assert "trend_intact" in ctx
        assert "fibonacci_retracements" in ctx

    def test_wave5_targets_in_report(self):
        analyzer = ElliottWaveAnalyzer(self.IMPULSE_PIVOTS, bullish=True)
        report = analyzer.analyze_impulse()
        assert "Wave5_38.2%" in report.wave5_targets

    def test_correction_trade_setup_zigzag(self):
        analyzer = ElliottWaveAnalyzer(
            [200.0, 150.0, 172.0, 110.0], bullish=False
        )
        report = analyzer.analyze_correction(correction_type="zigzag")
        if report.valid:
            assert report.trade_setup is not None

    def test_full_report_correction_4_pivots(self):
        # Supply only 4 pivots → correction analysis
        analyzer = ElliottWaveAnalyzer([200.0, 150.0, 172.0, 110.0], bullish=False)
        report = analyzer.full_report()
        assert report.pattern in {
            PatternType.ZIGZAG,
            PatternType.IRREGULAR_CORRECTION,
            PatternType.FLAT,
        }

    def test_check_impulse_wave_wrong_count(self):
        with pytest.raises(ValueError):
            check_impulse_wave([0, 100, 60], bullish=True)
