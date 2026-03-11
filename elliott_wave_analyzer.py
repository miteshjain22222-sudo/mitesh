"""
Elliott Wave Analyzer
=====================
Rules-based Elliott Wave analysis based on R.N. Elliott's Wave Principle
and Robert Prechter's "Elliott Wave Principle: Key to Market Behavior".

Rules enforced:
  Impulse Wave:
    1. Wave 2 never retraces more than 100% of Wave 1.
    2. Wave 3 is never the shortest impulse wave among Waves 1, 3, and 5.
    3. Wave 4 never overlaps the price territory of Wave 1 (except diagonal triangles).

  Corrective Wave (ABC):
    - Wave A subdivides into 5 waves (in zigzag) or 3 waves (in flat).
    - Wave B retraces 38.2%–100% of Wave A.
    - Wave C typically equals Wave A or extends to 161.8% of Wave A.

Fibonacci ratios used for targets:
  Retracement: 0.236, 0.382, 0.500, 0.618, 0.786
  Extension:   1.000, 1.272, 1.414, 1.618, 2.000, 2.618
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Fibonacci constants
# ---------------------------------------------------------------------------
FIBO_RETRACEMENTS = [0.236, 0.382, 0.500, 0.618, 0.786, 1.000]
FIBO_EXTENSIONS = [1.000, 1.272, 1.414, 1.618, 2.000, 2.618]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class WaveType(str, Enum):
    IMPULSE = "impulse"
    CORRECTIVE = "corrective"
    UNKNOWN = "unknown"


class WaveDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class PivotPoint:
    """A swing high or swing low detected in price data."""

    index: int          # bar index in the source series
    price: float        # price at the pivot
    is_high: bool       # True = swing high, False = swing low

    def __repr__(self) -> str:
        kind = "HIGH" if self.is_high else "LOW"
        return f"Pivot({kind} idx={self.index} price={self.price:.4f})"


@dataclass
class Wave:
    """Represents a single Elliott Wave leg."""

    label: str                    # "1","2","3","4","5" or "A","B","C"
    start: PivotPoint
    end: PivotPoint
    wave_type: WaveType = WaveType.UNKNOWN
    sub_waves: List["Wave"] = field(default_factory=list)

    @property
    def length(self) -> float:
        return abs(self.end.price - self.start.price)

    @property
    def direction(self) -> WaveDirection:
        if self.end.price > self.start.price:
            return WaveDirection.UP
        if self.end.price < self.start.price:
            return WaveDirection.DOWN
        return WaveDirection.UNKNOWN

    def retracement_of(self, other: "Wave") -> float:
        """Return the fraction this wave retraces the *other* wave (0–1+)."""
        if other.length == 0:
            return 0.0
        return self.length / other.length

    def __repr__(self) -> str:
        return (
            f"Wave({self.label} {self.direction.value} "
            f"{self.start.price:.4f}→{self.end.price:.4f} len={self.length:.4f})"
        )


@dataclass
class WaveTarget:
    """A projected price target derived from Fibonacci relationships."""

    wave_label: str       # which wave this is a target for
    ratio: float          # Fibonacci ratio applied
    price: float          # projected price
    ratio_type: str       # "retracement" or "extension"
    description: str      # human-readable description

    def __repr__(self) -> str:
        return (
            f"Target(Wave {self.wave_label} | {self.ratio_type} "
            f"{self.ratio:.3f} → {self.price:.4f} | {self.description})"
        )


@dataclass
class WaveCount:
    """A complete (or partial) Elliott Wave count."""

    waves: List[Wave]
    wave_type: WaveType
    direction: WaveDirection
    is_complete: bool
    next_wave_label: Optional[str]
    targets: List[WaveTarget]
    violations: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0

    def summary(self) -> str:
        lines = [
            f"Wave Count ({self.wave_type.value}, {self.direction.value})",
            f"  Waves identified : {[w.label for w in self.waves]}",
            f"  Complete         : {self.is_complete}",
            f"  Next wave        : {self.next_wave_label}",
            f"  Valid            : {self.is_valid}",
        ]
        if self.violations:
            lines.append("  Violations:")
            for v in self.violations:
                lines.append(f"    • {v}")
        if self.targets:
            lines.append("  Targets:")
            for t in self.targets:
                lines.append(f"    {t}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pivot detection
# ---------------------------------------------------------------------------


def detect_pivots(prices: List[float], left_bars: int = 3, right_bars: int = 3) -> List[PivotPoint]:
    """
    Detect swing highs and lows using a simple left/right bar look-around.

    A pivot HIGH at index *i* requires that *prices[i]* is strictly greater
    than every bar in the *left_bars* bars to its left and the *right_bars*
    bars to its right.  Pivot LOWs are the mirror image.

    Parameters
    ----------
    prices : List[float]
        Closing (or high/low) price series, oldest first.
    left_bars, right_bars : int
        Confirmation bars on each side.

    Returns
    -------
    List[PivotPoint] ordered by index.
    """
    pivots: List[PivotPoint] = []
    n = len(prices)
    for i in range(left_bars, n - right_bars):
        window_left = prices[i - left_bars: i]
        window_right = prices[i + 1: i + right_bars + 1]
        # Swing high
        if all(prices[i] > p for p in window_left) and all(prices[i] > p for p in window_right):
            pivots.append(PivotPoint(index=i, price=prices[i], is_high=True))
        # Swing low
        elif all(prices[i] < p for p in window_left) and all(prices[i] < p for p in window_right):
            pivots.append(PivotPoint(index=i, price=prices[i], is_high=False))
    return pivots


# ---------------------------------------------------------------------------
# Fibonacci helpers
# ---------------------------------------------------------------------------


def fibonacci_retracement_levels(
    wave_start: float, wave_end: float
) -> List[Tuple[float, float]]:
    """
    Return (ratio, price) pairs for standard retracement levels of a wave.

    The retracement is measured *back* from *wave_end* toward *wave_start*.
    """
    move = wave_end - wave_start
    return [(r, wave_end - move * r) for r in FIBO_RETRACEMENTS]


def fibonacci_extension_levels(
    wave_start: float, wave_end: float, reference_start: float
) -> List[Tuple[float, float]]:
    """
    Return (ratio, price) pairs for extension targets.

    The extension is projected from *reference_start* using the magnitude of
    the wave from *wave_start* to *wave_end*.
    """
    move = abs(wave_end - wave_start)
    direction = 1 if wave_end > wave_start else -1
    return [(r, reference_start + direction * move * r) for r in FIBO_EXTENSIONS]


# ---------------------------------------------------------------------------
# Elliott Wave rules
# ---------------------------------------------------------------------------


def validate_impulse_wave(waves: List[Wave]) -> List[str]:
    """
    Validate a 5-wave impulse against the three hard Elliott Wave rules.

    Parameters
    ----------
    waves : List[Wave]
        Exactly 5 Wave objects in order [W1, W2, W3, W4, W5].

    Returns
    -------
    List[str]  – list of violation messages (empty = valid).
    """
    if len(waves) < 2:
        return []

    violations: List[str] = []

    w1 = waves[0] if len(waves) > 0 else None
    w2 = waves[1] if len(waves) > 1 else None
    w3 = waves[2] if len(waves) > 2 else None
    w4 = waves[3] if len(waves) > 3 else None
    w5 = waves[4] if len(waves) > 4 else None

    # Rule 1: Wave 2 never retraces more than 100% of Wave 1
    if w1 and w2:
        ratio = w2.retracement_of(w1)
        if ratio > 1.0:
            violations.append(
                f"Rule 1 violated: Wave 2 retraced {ratio:.1%} of Wave 1 (must be ≤100%)."
            )

    # Rule 2: Wave 3 is never the shortest impulse wave
    if w1 and w3:
        # Compare Wave 3 only against the OTHER motive waves (W1 and W5).
        # Including W3 in the min() would make the check trivially impossible.
        other_motive = {"Wave 1": w1.length}
        if w5:
            other_motive["Wave 5"] = w5.length
        all_lengths = {"Wave 1": w1.length, "Wave 3": w3.length}
        if w5:
            all_lengths["Wave 5"] = w5.length
        if w3.length < min(other_motive.values()):
            violations.append(
                f"Rule 2 violated: Wave 3 ({w3.length:.4f}) is the shortest "
                f"motive wave. Lengths: {all_lengths}."
            )

    # Rule 3: Wave 4 must not overlap Wave 1's price territory
    if w1 and w4:
        # Determine the price territory of Wave 1
        w1_high = max(w1.start.price, w1.end.price)
        w1_low = min(w1.start.price, w1.end.price)
        w4_high = max(w4.start.price, w4.end.price)
        w4_low = min(w4.start.price, w4.end.price)
        overlaps = w4_low < w1_high and w4_high > w1_low
        if overlaps:
            violations.append(
                f"Rule 3 violated: Wave 4 overlaps Wave 1's price territory "
                f"(W1: {w1_low:.4f}–{w1_high:.4f}, W4: {w4_low:.4f}–{w4_high:.4f})."
            )

    return violations


def validate_corrective_wave(waves: List[Wave]) -> List[str]:
    """
    Validate a 3-wave (A-B-C) corrective pattern.

    Parameters
    ----------
    waves : List[Wave]
        2 or 3 Wave objects in order [WA, WB, WC].

    Returns
    -------
    List[str]  – list of violation messages (empty = valid).
    """
    if len(waves) < 2:
        return []

    violations: List[str] = []
    wa = waves[0]
    wb = waves[1]
    wc = waves[2] if len(waves) > 2 else None

    # Wave B must retrace at least 38.2% and not more than 100% of Wave A
    ratio_b = wb.retracement_of(wa)
    if ratio_b < 0.236:
        violations.append(
            f"Corrective rule: Wave B retraced only {ratio_b:.1%} of Wave A "
            f"(expected ≥23.6%)."
        )
    if ratio_b > 1.0:
        violations.append(
            f"Corrective rule: Wave B retraced {ratio_b:.1%} of Wave A (must be ≤100%)."
        )

    # Wave C typically extends toward 61.8%–161.8% of Wave A
    if wc:
        ratio_c = wc.retracement_of(wa)
        if ratio_c < 0.618:
            violations.append(
                f"Corrective guideline: Wave C ({ratio_c:.1%} of Wave A) "
                f"is shorter than typical (≥61.8% of Wave A)."
            )

    return violations


# ---------------------------------------------------------------------------
# Target projections
# ---------------------------------------------------------------------------


def project_next_wave_targets(
    completed_waves: List[Wave], next_wave_label: str
) -> List[WaveTarget]:
    """
    Project Fibonacci targets for the *next* wave given the waves completed so far.

    Parameters
    ----------
    completed_waves : List[Wave]
        Waves that have already been confirmed.
    next_wave_label : str
        Label of the wave to project ("1"–"5" or "A"/"B"/"C").

    Returns
    -------
    List[WaveTarget]
    """
    targets: List[WaveTarget] = []
    n = len(completed_waves)

    def _add_retracements(ref_wave: Wave, label: str, context: str) -> None:
        for ratio, price in fibonacci_retracement_levels(ref_wave.start.price, ref_wave.end.price):
            targets.append(
                WaveTarget(
                    wave_label=label,
                    ratio=ratio,
                    price=price,
                    ratio_type="retracement",
                    description=f"{context} | {ratio:.1%} retracement of Wave {ref_wave.label}",
                )
            )

    def _add_extensions(base_wave: Wave, reference_start: float, label: str, context: str) -> None:
        for ratio, price in fibonacci_extension_levels(
            base_wave.start.price, base_wave.end.price, reference_start
        ):
            targets.append(
                WaveTarget(
                    wave_label=label,
                    ratio=ratio,
                    price=price,
                    ratio_type="extension",
                    description=f"{context} | {ratio:.3f}× extension of Wave {base_wave.label}",
                )
            )

    # --- Impulse wave targets ---
    if next_wave_label == "2" and n >= 1:
        _add_retracements(completed_waves[0], "2", "Wave 2 typical retracement of Wave 1")

    elif next_wave_label == "3" and n >= 2:
        w1 = completed_waves[0]
        w2_end = completed_waves[1].end.price
        _add_extensions(w1, w2_end, "3", "Wave 3 extension from Wave 2 low")

    elif next_wave_label == "4" and n >= 3:
        _add_retracements(completed_waves[2], "4", "Wave 4 typical retracement of Wave 3")

    elif next_wave_label == "5" and n >= 4:
        w1 = completed_waves[0]
        w4_end = completed_waves[3].end.price
        _add_extensions(w1, w4_end, "5", "Wave 5 projection from Wave 4 end")
        # Wave 5 = Wave 1 target
        w5_equal_w1 = w4_end + (w1.end.price - w1.start.price) * (
            1 if w1.direction == WaveDirection.UP else -1
        )
        targets.append(
            WaveTarget(
                wave_label="5",
                ratio=1.0,
                price=w5_equal_w1,
                ratio_type="extension",
                description="Wave 5 = Wave 1 (equality target)",
            )
        )

    # --- Corrective wave targets ---
    elif next_wave_label == "B" and n >= 1:
        _add_retracements(completed_waves[0], "B", "Wave B retracement of Wave A")

    elif next_wave_label == "C" and n >= 2:
        wa = completed_waves[0]
        wb_end = completed_waves[1].end.price
        _add_extensions(wa, wb_end, "C", "Wave C extension from Wave B end")
        # Wave C = Wave A (equality)
        direction = 1 if wa.direction == WaveDirection.DOWN else -1
        c_equal_a = wb_end + direction * wa.length
        targets.append(
            WaveTarget(
                wave_label="C",
                ratio=1.0,
                price=c_equal_a,
                ratio_type="extension",
                description="Wave C = Wave A (equality target)",
            )
        )

    return targets


# ---------------------------------------------------------------------------
# Main analyser
# ---------------------------------------------------------------------------


class ElliottWaveAnalyzer:
    """
    High-level Elliott Wave analyser.

    Usage
    -----
    >>> prices = [100, 105, 102, 112, 108, 120, 115, 118]
    >>> analyzer = ElliottWaveAnalyzer(prices, left_bars=2, right_bars=2)
    >>> count = analyzer.analyze()
    >>> print(count.summary())
    """

    def __init__(
        self,
        prices: List[float],
        left_bars: int = 3,
        right_bars: int = 3,
    ) -> None:
        self.prices = prices
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.pivots: List[PivotPoint] = []
        self._wave_count: Optional[WaveCount] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> WaveCount:
        """
        Run the full Elliott Wave analysis pipeline.

        Returns the best WaveCount found (impulse preferred over corrective).
        """
        self.pivots = detect_pivots(self.prices, self.left_bars, self.right_bars)
        if len(self.pivots) < 2:
            return WaveCount(
                waves=[],
                wave_type=WaveType.UNKNOWN,
                direction=WaveDirection.UNKNOWN,
                is_complete=False,
                next_wave_label=None,
                targets=[],
                violations=["Not enough pivot points detected."],
            )

        impulse_count = self._try_impulse_count()
        corrective_count = self._try_corrective_count()

        # Prefer the count with more valid waves
        if impulse_count.is_valid and len(impulse_count.waves) >= len(
            corrective_count.waves if corrective_count.is_valid else []
        ):
            self._wave_count = impulse_count
        elif corrective_count.is_valid:
            self._wave_count = corrective_count
        else:
            # Return impulse even if invalid so violations are surfaced
            self._wave_count = impulse_count

        return self._wave_count

    def get_current_wave_count(self) -> Optional[WaveCount]:
        """Return the most recently computed WaveCount."""
        return self._wave_count

    def get_fibonacci_levels(self, wave_start: float, wave_end: float) -> dict:
        """
        Convenience method: return all Fibonacci retracement and extension
        levels for a given price move.
        """
        return {
            "retracements": fibonacci_retracement_levels(wave_start, wave_end),
            "extensions": fibonacci_extension_levels(wave_start, wave_end, wave_end),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_wave(self, label: str, start: PivotPoint, end: PivotPoint, wtype: WaveType) -> Wave:
        return Wave(label=label, start=start, end=end, wave_type=wtype)

    def _try_impulse_count(self) -> WaveCount:
        """Attempt to fit a 5-wave impulse to the pivots."""
        pivots = self.pivots
        best_waves: List[Wave] = []
        best_violations: List[str] = []
        best_targets: List[WaveTarget] = []
        best_direction = WaveDirection.UNKNOWN

        # Try every possible starting pivot, alternating high/low
        for start_idx in range(len(pivots)):
            waves: List[Wave] = []
            labels = ["1", "2", "3", "4", "5"]
            current_pivots = [pivots[start_idx]]

            for label in labels:
                next_pivot_idx = pivots.index(current_pivots[-1]) + 1
                if next_pivot_idx >= len(pivots):
                    break
                next_pivot = pivots[next_pivot_idx]

                # Direction alternates: odd waves = motive, even = corrective
                wave_num = int(label)
                if wave_num % 2 == 1:
                    wtype = WaveType.IMPULSE
                else:
                    wtype = WaveType.CORRECTIVE
                waves.append(
                    self._build_wave(label, current_pivots[-1], next_pivot, wtype)
                )
                current_pivots.append(next_pivot)

            if not waves:
                continue

            violations = validate_impulse_wave(waves)
            if len(waves) > len(best_waves) and len(violations) <= len(best_violations):
                best_waves = waves
                best_violations = violations
                # Infer direction from Wave 1
                best_direction = waves[0].direction

        is_complete = len(best_waves) == 5
        next_label: Optional[str] = None
        if not is_complete and best_waves:
            next_labels = ["1", "2", "3", "4", "5"]
            used = [w.label for w in best_waves]
            remaining = [l for l in next_labels if l not in used]
            next_label = remaining[0] if remaining else None

        targets = project_next_wave_targets(best_waves, next_label) if next_label else []
        return WaveCount(
            waves=best_waves,
            wave_type=WaveType.IMPULSE,
            direction=best_direction,
            is_complete=is_complete,
            next_wave_label=next_label,
            targets=targets,
            violations=best_violations,
        )

    def _try_corrective_count(self) -> WaveCount:
        """Attempt to fit a 3-wave A-B-C corrective to the pivots."""
        pivots = self.pivots
        best_waves: List[Wave] = []
        best_violations: List[str] = []
        best_targets: List[WaveTarget] = []
        best_direction = WaveDirection.UNKNOWN

        for start_idx in range(len(pivots) - 1):
            waves: List[Wave] = []
            labels = ["A", "B", "C"]
            current_pivot = pivots[start_idx]
            for label in labels:
                next_idx = pivots.index(current_pivot) + 1
                if next_idx >= len(pivots):
                    break
                next_pivot = pivots[next_idx]
                waves.append(
                    self._build_wave(label, current_pivot, next_pivot, WaveType.CORRECTIVE)
                )
                current_pivot = next_pivot

            if not waves:
                continue

            violations = validate_corrective_wave(waves)
            if len(waves) > len(best_waves) and len(violations) <= len(best_violations):
                best_waves = waves
                best_violations = violations
                best_direction = waves[0].direction

        is_complete = len(best_waves) == 3
        next_label = None
        if not is_complete and best_waves:
            used = [w.label for w in best_waves]
            for lbl in ["A", "B", "C"]:
                if lbl not in used:
                    next_label = lbl
                    break

        targets = project_next_wave_targets(best_waves, next_label) if next_label else []
        return WaveCount(
            waves=best_waves,
            wave_type=WaveType.CORRECTIVE,
            direction=best_direction,
            is_complete=is_complete,
            next_wave_label=next_label,
            targets=targets,
            violations=best_violations,
        )

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise the current WaveCount to a JSON string."""
        if self._wave_count is None:
            return json.dumps({})

        def wave_dict(w: Wave) -> dict:
            return {
                "label": w.label,
                "start_index": w.start.index,
                "start_price": w.start.price,
                "end_index": w.end.index,
                "end_price": w.end.price,
                "length": w.length,
                "direction": w.direction.value,
                "wave_type": w.wave_type.value,
            }

        def target_dict(t: WaveTarget) -> dict:
            return {
                "wave_label": t.wave_label,
                "ratio": t.ratio,
                "price": t.price,
                "ratio_type": t.ratio_type,
                "description": t.description,
            }

        wc = self._wave_count
        return json.dumps(
            {
                "wave_type": wc.wave_type.value,
                "direction": wc.direction.value,
                "is_complete": wc.is_complete,
                "is_valid": wc.is_valid,
                "next_wave_label": wc.next_wave_label,
                "waves": [wave_dict(w) for w in wc.waves],
                "targets": [target_dict(t) for t in wc.targets],
                "violations": wc.violations,
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Quick demo / standalone usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Hand-crafted price series that forms a clear 5-wave bullish impulse followed
    # by an A-B-C correction.  Replace with real OHLC closes for live analysis.
    sample_prices = [
        # Wave 1 up
        100.0, 101.0, 103.0, 106.0, 110.0,
        # Wave 2 down (~50% retrace of W1)
        108.0, 106.0, 105.0,
        # Wave 3 up (longest)
        107.0, 110.0, 114.0, 119.0, 125.0,
        # Wave 4 down (~38% retrace of W3)
        123.0, 121.0, 119.0,
        # Wave 5 up (≈ W1 length)
        120.0, 122.0, 125.0, 128.0, 130.0,
        # Wave A down
        128.0, 125.0, 122.0, 119.0,
        # Wave B up (~50% retrace of A)
        120.0, 122.0, 124.0,
        # Wave C down (≈ A length)
        122.0, 119.0, 116.0, 113.0,
    ]

    print("Elliott Wave Analyzer")
    print("=" * 50)
    analyzer = ElliottWaveAnalyzer(sample_prices, left_bars=2, right_bars=2)
    count = analyzer.analyze()

    print(count.summary())
    print()
    print("Pivots detected:")
    for p in analyzer.pivots:
        print(f"  {p}")

    print()
    print("JSON output:")
    print(analyzer.to_json())
