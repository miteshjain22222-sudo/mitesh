"""
High-level Elliott Wave analyzer.

Combines Fibonacci calculations, core rules, and pattern detection into a
single convenient ``ElliottWaveAnalyzer`` class.

Typical usage::

    from elliott_wave import ElliottWaveAnalyzer

    # 5-wave impulse pivots [W0, W1, W2, W3, W4, W5]
    pivots = [100, 150, 120, 200, 160, 230]
    analyzer = ElliottWaveAnalyzer(pivots, bullish=True)
    report = analyzer.full_report()
    print(report)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .fibonacci import (
    RATIO_23,
    RATIO_38,
    RATIO_61,
    RATIO_100,
    retracement_levels_for,
    projection_levels_for,
    retracement_ratio,
    wave_length,
)
from .patterns import (
    PatternResult,
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
from .rules import (
    RuleResult,
    check_wave2_retrace,
    check_wave3_not_shortest,
    check_wave4_no_overlap,
    check_wave5_qualification,
    check_38pct_breakout,
    alternation_check,
    classify_wave3,
    classify_wave5,
)


@dataclass
class WaveReport:
    """Consolidated analysis report for an Elliott Wave count."""

    pattern: PatternType
    valid: bool
    rule_results: List[RuleResult] = field(default_factory=list)
    pattern_result: Optional[PatternResult] = None
    fibonacci_levels: dict = field(default_factory=dict)
    wave5_targets: dict = field(default_factory=dict)
    trade_setup: Optional[dict] = None
    summary: str = ""

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"Pattern : {self.pattern.value}",
            f"Valid   : {self.valid}",
            f"Summary : {self.summary}",
        ]
        if self.rule_results:
            lines.append("\nRule Checks:")
            for r in self.rule_results:
                status = "✓" if r.passed else "✗"
                lines.append(f"  [{status}] {r.rule}: {r.reason}")
        if self.wave5_targets:
            lines.append("\nWave 5 / Next-Wave Targets:")
            for label, price in self.wave5_targets.items():
                lines.append(f"  {label}: {price:.4f}")
        if self.trade_setup:
            lines.append("\nTrade Setup (38% Breakout):")
            ts = self.trade_setup
            ez = ts.get("entry_zone", ("–", "–"))
            lines.append(f"  Entry zone : {ez[0]:.4f} – {ez[1]:.4f}")
            lines.append(f"  Stop loss  : {ts.get('stop_loss', '–'):.4f}")
            lines.append(f"  Target 1   : {ts.get('target_1', '–'):.4f}")
            lines.append(f"  Target 2   : {ts.get('target_2', '–'):.4f}")
        return "\n".join(lines)


class ElliottWaveAnalyzer:
    """Analyze a sequence of price pivots for Elliott Wave patterns.

    Args:
        pivots:  Ordered list of price pivots.
                 For a 5-wave impulse provide 6 values: [W0, W1, W2, W3, W4, W5].
                 For an A-B-C correction provide 4 values: [A_start, A_end, B_end, C_end].
        bullish: True if the primary trend is upward, False for downward.
    """

    def __init__(self, pivots: List[float], bullish: bool = True) -> None:
        self.pivots = pivots
        self.bullish = bullish

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_impulse(self, is_diagonal: bool = False) -> WaveReport:
        """Validate and analyse a 5-wave impulse (or diagonal) pattern.

        Args:
            is_diagonal: Set True if this is a Leading/Ending Diagonal.

        Returns:
            WaveReport with full rule checks and projected targets.

        Raises:
            ValueError: If fewer than 6 pivots were supplied.
        """
        if len(self.pivots) < 6:
            raise ValueError(
                "Impulse analysis requires 6 pivots [W0..W5]. "
                f"Got {len(self.pivots)}."
            )

        w0, w1, w2, w3, w4, w5 = self.pivots[:6]
        pattern_type = (
            PatternType.ENDING_DIAGONAL
            if is_diagonal
            else PatternType.IMPULSE
        )

        if is_diagonal:
            pr = detect_ending_diagonal(self.pivots[:6], self.bullish)
        else:
            pr = detect_impulse(self.pivots[:6], self.bullish)

        # Fibonacci levels for each wave
        fib_levels = {
            "Wave1": retracement_levels_for(w0, w1),
            "Wave2": retracement_levels_for(w0, w1),  # retracement of W1
            "Wave3": projection_levels_for(w0, w1, w2),
            "Wave4": retracement_levels_for(w2, w3),
            "Wave5": projection_levels_for(w2, w3, w4),
        }

        # Wave 5 qualification check
        w5_qual = check_wave5_qualification(w3, w4, w5, self.bullish)

        # Alternation check (Wave 2 vs Wave 4 retracement)
        w2_retrace = retracement_ratio(w0, w1, w2)
        w4_retrace = retracement_ratio(w2, w3, w4)
        alt_check = alternation_check(w2_retrace, w4_retrace)

        all_rules = (pr.reasons if pr else [])
        rule_results = [w5_qual, alt_check]

        summary = (
            f"{'Valid' if pr.passed else 'Invalid'} {pattern_type.value}. "
            f"Wave 5 {'qualifies' if w5_qual.passed else 'does NOT qualify'}. "
            f"Alternation: {'observed' if alt_check.passed else 'NOT observed'}."
        )

        return WaveReport(
            pattern=pattern_type,
            valid=pr.passed and w5_qual.passed,
            rule_results=rule_results,
            pattern_result=pr,
            fibonacci_levels=fib_levels,
            wave5_targets=pr.targets if pr.targets else {},
            summary=summary,
        )

    def analyze_correction(self, correction_type: str = "auto") -> WaveReport:
        """Analyse a 3-wave (A-B-C) corrective pattern.

        Args:
            correction_type: One of ``"zigzag"``, ``"irregular"``, ``"flat"``,
                             or ``"auto"`` to try all and return the first match.

        Returns:
            WaveReport.

        Raises:
            ValueError: If fewer than 4 pivots were supplied.
        """
        if len(self.pivots) < 4:
            raise ValueError(
                "Correction analysis requires 4 pivots [A_start, A_end, B_end, C_end]. "
                f"Got {len(self.pivots)}."
            )

        a_start, a_end, b_end, c_end = self.pivots[:4]

        candidates: List[PatternResult] = []

        if correction_type in ("zigzag", "auto"):
            candidates.append(
                detect_zigzag(a_start, a_end, b_end, c_end, self.bullish)
            )
        if correction_type in ("irregular", "auto"):
            candidates.append(
                detect_irregular_correction(
                    a_start, a_end, b_end, c_end, self.bullish
                )
            )
        if correction_type in ("flat", "auto"):
            candidates.append(
                detect_flat_correction(a_start, a_end, b_end, c_end)
            )

        # Pick first valid match (or last attempted if none valid)
        best = next((c for c in candidates if c.passed), candidates[-1])

        trade_setup = None
        if best.pattern == PatternType.ZIGZAG and best.passed:
            trade_setup = zigzag_trade_setup(
                a_start, a_end, b_end, c_end, self.bullish
            )

        fib_levels = {
            "WaveA": retracement_levels_for(a_start, a_end),
            "WaveB": retracement_levels_for(a_start, a_end),
            "WaveC": projection_levels_for(a_start, a_end, b_end),
        }

        return WaveReport(
            pattern=best.pattern,
            valid=best.passed,
            pattern_result=best,
            fibonacci_levels=fib_levels,
            trade_setup=trade_setup,
            summary=(
                f"{'Valid' if best.passed else 'Invalid'} {best.pattern.value} "
                "corrective pattern."
            ),
        )

    def current_wave_context(self, current_price: float) -> dict:
        """Provide real-time wave context for the current market price.

        Uses 38% retracement logic (Chapter 18) to indicate whether the trend
        is intact or a reversal is developing.

        Requires at least 4 pivots: the last completed Wave 3 start/end and
        the Wave 4 endpoint are derived from self.pivots.

        Args:
            current_price: Latest traded price.

        Returns:
            Dictionary with Fibonacci levels and a breakout assessment.
        """
        if len(self.pivots) < 4:
            return {"error": "Need at least 4 pivots for wave context."}

        # Use last four pivots as Wave 3 start / Wave 3 end proxy
        w_start = self.pivots[-4]
        w_end = self.pivots[-2]

        levels = retracement_levels_for(w_start, w_end)
        breakout = check_38pct_breakout(w_start, w_end, current_price, self.bullish)

        return {
            "current_price": current_price,
            "fibonacci_retracements": levels,
            "38pct_level": levels.get("38.2%"),
            "23pct_level": levels.get("23.6%"),
            "breakout_status": breakout.reason,
            "trend_intact": breakout.passed,
        }

    def full_report(self) -> WaveReport:
        """Auto-detect pattern type and return the most relevant report.

        Returns:
            WaveReport for a 5-wave impulse if 6 pivots are supplied,
            otherwise a corrective wave report.
        """
        if len(self.pivots) >= 6:
            return self.analyze_impulse()
        return self.analyze_correction()
