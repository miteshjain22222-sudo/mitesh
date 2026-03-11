"""
Elliott Wave Theory - Rule-Based Python Implementation
======================================================

Rules implemented (classical Elliott Wave theory):

IMPULSE WAVE RULES (waves 1-5):
  Rule 1: Wave 2 never retraces more than 100 % of Wave 1.
  Rule 2: Wave 3 is never the shortest of Waves 1, 3, and 5.
  Rule 3: Wave 4 never overlaps (enters the price territory of) Wave 1.

CORRECTIVE WAVE RULES (ABC pattern):
  Rule 1: Wave B never retraces more than 100 % of Wave A.
  Rule 2: Wave C typically extends beyond the end of Wave A.

FIBONACCI GUIDELINES:
  Wave 2 commonly retraces  50.0 % or 61.8 % of Wave 1.
  Wave 3 commonly extends  161.8 % of Wave 1.
  Wave 4 commonly retraces  38.2 % of Wave 3.
  Wave 5 equals Wave 1  or  61.8 % of the net move from Wave 1 start to Wave 3 end.
  Wave B commonly retraces  50.0 % or 61.8 % of Wave A.
  Wave C equals Wave A  or  161.8 % of Wave A.

Usage:
    import pandas as pd
    from elliott_wave import ElliottWaveAnalyzer

    df = pd.read_csv("ohlcv.csv", parse_dates=["date"])
    analyzer = ElliottWaveAnalyzer(df, pivot_len=5)
    result = analyzer.analyze()
    print(result["waves"])      # detected waves
    print(result["targets"])    # next-wave Fibonacci targets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Standard Fibonacci ratios used in Elliott Wave analysis
FIB_RATIOS = {
    "0.236": 0.236,
    "0.382": 0.382,
    "0.500": 0.500,
    "0.618": 0.618,
    "0.786": 0.786,
    "1.000": 1.000,
    "1.272": 1.272,
    "1.618": 1.618,
    "2.000": 2.000,
    "2.618": 2.618,
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Pivot:
    """A single pivot point (swing high or swing low)."""
    index: int          # bar index in the data
    price: float
    is_high: bool       # True = swing high, False = swing low

    @property
    def kind(self) -> str:
        return "HIGH" if self.is_high else "LOW"

    def __repr__(self) -> str:
        return f"Pivot({self.kind} @ bar={self.index}, price={self.price:.4f})"


@dataclass
class Wave:
    """A single Elliott Wave leg."""
    label: str          # '1','2','3','4','5'  or  'A','B','C'
    start: Pivot
    end: Pivot
    wave_type: str      # 'impulse' or 'corrective'

    @property
    def length(self) -> float:
        """Absolute price distance of the wave."""
        return abs(self.end.price - self.start.price)

    @property
    def direction(self) -> str:
        return "UP" if self.end.price > self.start.price else "DOWN"

    def retracement_of(self, other: "Wave") -> float:
        """
        Return what fraction of *other* this wave retraces (0–1+).
        A value > 1 means a full retracement (invalidation).
        """
        if other.length == 0:
            return 0.0
        return self.length / other.length

    def __repr__(self) -> str:
        return (
            f"Wave({self.label} [{self.wave_type}] "
            f"{self.direction} "
            f"start={self.start.price:.4f} end={self.end.price:.4f} "
            f"len={self.length:.4f})"
        )


@dataclass
class WaveSequence:
    """A validated sequence of Elliott Waves."""
    waves: List[Wave]
    sequence_type: str              # 'impulse_bull','impulse_bear','abc_bull','abc_bear'
    rules_passed: List[str] = field(default_factory=list)
    rules_failed: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.rules_failed) == 0

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"WaveSequence({self.sequence_type} | {status} | "
            f"waves={[w.label for w in self.waves]})"
        )


@dataclass
class FibTarget:
    """A Fibonacci price target for the next wave."""
    label: str          # e.g. "Wave 6 (new W1): 61.8%"
    ratio: float
    price: float
    description: str


# ─────────────────────────────────────────────────────────────────────────────
# FIBONACCI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fib_retracement(start: float, end: float, ratio: float) -> float:
    """Price at *ratio* retracement from *end* back toward *start*."""
    return end - (end - start) * ratio


def fib_extension(start: float, end: float, ratio: float) -> float:
    """Price at *ratio* extension beyond *end*, measured from *start*."""
    return start + (end - start) * ratio


def fib_projection(wave_start: float, wave_end: float,
                   project_from: float, ratio: float) -> float:
    """
    Project a Fibonacci multiple of wave (start→end) starting from
    *project_from* (used for Wave 3 / Wave C projections).
    """
    wave_len = abs(wave_end - wave_start)
    direction = 1 if wave_end > wave_start else -1
    return project_from + direction * wave_len * ratio


# ─────────────────────────────────────────────────────────────────────────────
# PIVOT DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def find_pivots(
    highs: List[float],
    lows: List[float],
    pivot_len: int = 5,
) -> List[Pivot]:
    """
    Detect swing highs and swing lows using the classic *n*-bar
    left/right confirmation method.

    A bar is a **pivot high** if its *high* is the highest over
    [i-pivot_len … i+pivot_len].

    A bar is a **pivot low** if its *low* is the lowest over the
    same window.

    Returns a time-ordered list of Pivot objects, alternating
    between highs and lows (duplicate consecutive pivots of the
    same type are resolved by keeping the more extreme one).
    """
    n = len(highs)
    raw: List[Pivot] = []

    for i in range(pivot_len, n - pivot_len):
        window_high = highs[i - pivot_len: i + pivot_len + 1]
        window_low  = lows [i - pivot_len: i + pivot_len + 1]

        if highs[i] == max(window_high):
            raw.append(Pivot(index=i, price=highs[i], is_high=True))

        if lows[i] == min(window_low):
            raw.append(Pivot(index=i, price=lows[i],  is_high=False))

    # Sort by bar index, then enforce alternation (keep more extreme pivot)
    raw.sort(key=lambda p: (p.index, not p.is_high))

    alternating: List[Pivot] = []
    for pivot in raw:
        if not alternating:
            alternating.append(pivot)
        elif alternating[-1].is_high == pivot.is_high:
            # Same direction: keep the more extreme one
            if pivot.is_high and pivot.price > alternating[-1].price:
                alternating[-1] = pivot
            elif not pivot.is_high and pivot.price < alternating[-1].price:
                alternating[-1] = pivot
        else:
            alternating.append(pivot)

    return alternating


# ─────────────────────────────────────────────────────────────────────────────
# ELLIOTT WAVE RULE VALIDATORS
# ─────────────────────────────────────────────────────────────────────────────

def validate_impulse(
    p0: Pivot,  # Wave 1 start
    p1: Pivot,  # Wave 1 end / Wave 2 start
    p2: Pivot,  # Wave 2 end / Wave 3 start
    p3: Pivot,  # Wave 3 end / Wave 4 start
    p4: Pivot,  # Wave 4 end / Wave 5 start
    p5: Pivot,  # Wave 5 end
) -> Tuple[List[str], List[str]]:
    """
    Validate the three hard rules for an impulse wave sequence.

    Returns (rules_passed, rules_failed).
    """
    passed: List[str] = []
    failed: List[str] = []

    bullish = p1.price > p0.price   # Wave 1 direction

    w1 = abs(p1.price - p0.price)
    w2 = abs(p2.price - p1.price)
    w3 = abs(p3.price - p2.price)
    w4 = abs(p4.price - p3.price)
    w5 = abs(p5.price - p4.price)

    # ── Rule 1: Wave 2 retracement < 100 % of Wave 1
    if bullish:
        rule1_ok = p2.price > p0.price
    else:
        rule1_ok = p2.price < p0.price

    if rule1_ok:
        passed.append("Rule 1 PASS: Wave 2 did not retrace > 100% of Wave 1")
    else:
        failed.append("Rule 1 FAIL: Wave 2 retraced > 100% of Wave 1")

    # ── Rule 2: Wave 3 is not the shortest among W1, W3, W5
    rule2_ok = not (w3 < w1 and w3 < w5)
    if rule2_ok:
        passed.append(
            f"Rule 2 PASS: Wave 3 ({w3:.4f}) is NOT the shortest "
            f"(W1={w1:.4f}, W5={w5:.4f})"
        )
    else:
        failed.append(
            f"Rule 2 FAIL: Wave 3 ({w3:.4f}) IS the shortest "
            f"(W1={w1:.4f}, W5={w5:.4f})"
        )

    # ── Rule 3: Wave 4 does not overlap Wave 1 territory
    if bullish:
        # Wave 1 top is p1.price; Wave 4 bottom must stay above it
        rule3_ok = p4.price > p1.price
    else:
        # Wave 1 bottom is p1.price; Wave 4 top must stay below it
        rule3_ok = p4.price < p1.price

    if rule3_ok:
        passed.append("Rule 3 PASS: Wave 4 did not overlap Wave 1 territory")
    else:
        failed.append("Rule 3 FAIL: Wave 4 overlapped Wave 1 territory")

    return passed, failed


def validate_abc(
    pA0: Pivot,  # Wave A start
    pA1: Pivot,  # Wave A end / Wave B start
    pB:  Pivot,  # Wave B end / Wave C start
    pC:  Pivot,  # Wave C end
) -> Tuple[List[str], List[str]]:
    """
    Validate the hard rule for an ABC corrective pattern.

    Returns (rules_passed, rules_failed).
    """
    passed: List[str] = []
    failed: List[str] = []

    wA = abs(pA1.price - pA0.price)
    wB = abs(pB.price  - pA1.price)

    # Rule: Wave B does not retrace more than 100 % of Wave A
    bearish_A = pA1.price < pA0.price   # A goes down

    if bearish_A:
        rule_ok = pB.price < pA0.price
    else:
        rule_ok = pB.price > pA0.price

    if rule_ok:
        pct = wB / wA * 100 if wA else 0
        passed.append(
            f"ABC Rule 1 PASS: Wave B retraced {pct:.1f}% of Wave A "
            f"(must be < 100%)"
        )
    else:
        failed.append("ABC Rule 1 FAIL: Wave B retraced > 100% of Wave A")

    return passed, failed


# ─────────────────────────────────────────────────────────────────────────────
# FIBONACCI TARGET CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def impulse_targets_after_wave5(
    p0: Pivot,   # Wave 1 start
    p1: Pivot,   # Wave 1 end
    p2: Pivot,   # Wave 2 end
    p3: Pivot,   # Wave 3 end
    p5: Pivot,   # Wave 5 end (current position)
) -> List[FibTarget]:
    """
    After a completed 5-wave impulse, calculate likely corrective
    ABC targets (retracements of the full 1–5 move).
    """
    targets: List[FibTarget] = []
    bullish = p1.price > p0.price
    wave5_end = p5.price
    wave1_start = p0.price

    # Common Wave A (first corrective leg) retracement levels
    for ratio, pct in [(0.382, "38.2"), (0.500, "50.0"), (0.618, "61.8")]:
        price = fib_retracement(wave1_start, wave5_end, ratio)
        targets.append(FibTarget(
            label=f"Corrective Wave A: {pct}% retracement",
            ratio=ratio,
            price=price,
            description=(
                f"Wave A target: price retraces {pct}% of the entire "
                f"5-wave move back toward {price:.4f}"
            ),
        ))

    # Maximum wave B cannot exceed Wave 1 start (100% retracement of 5-wave)
    targets.append(FibTarget(
        label="Wave B maximum (100% – W1 base)",
        ratio=1.000,
        price=wave1_start,
        description=(
            f"Wave B must not retrace beyond {wave1_start:.4f} "
            f"(Wave 1 start / 100% retracement of full impulse)"
        ),
    ))

    return targets


def corrective_targets_after_abc(
    pA0: Pivot,  # A start
    pA1: Pivot,  # A end
    pB:  Pivot,  # B end
    pC:  Pivot,  # C end (current position)
) -> List[FibTarget]:
    """
    After a completed ABC correction, calculate likely next impulse
    Wave 1 targets (extensions of the C wave).
    """
    targets: List[FibTarget] = []

    wC = abs(pC.price - pB.price)
    bullish_C = pA0.price < pA1.price   # Corrective goes up → next impulse goes up

    for ratio, pct in [(0.618, "61.8"), (1.000, "100"), (1.618, "161.8")]:
        if bullish_C:
            price = pC.price + wC * ratio
        else:
            price = pC.price - wC * ratio
        targets.append(FibTarget(
            label=f"Next Impulse W1 target: {pct}% of C wave",
            ratio=ratio,
            price=price,
            description=(
                f"After ABC ends at {pC.price:.4f}, next impulse Wave 1 "
                f"may reach {price:.4f} ({pct}% extension of Wave C)"
            ),
        ))

    return targets


def wave3_target(p0: Pivot, p1: Pivot, p2: Pivot) -> List[FibTarget]:
    """
    After Wave 2 end, project likely Wave 3 targets
    (1.618 × Wave 1, starting from Wave 2 end).
    """
    targets: List[FibTarget] = []
    for ratio, pct in [(1.000, "100"), (1.618, "161.8"), (2.618, "261.8")]:
        price = fib_projection(p0.price, p1.price, p2.price, ratio)
        targets.append(FibTarget(
            label=f"Wave 3 target: {pct}% of Wave 1",
            ratio=ratio,
            price=price,
            description=(
                f"Wave 3 projected to {price:.4f} "
                f"({pct}% of Wave 1 length from Wave 2 end {p2.price:.4f})"
            ),
        ))
    return targets


def wave4_target(p2: Pivot, p3: Pivot) -> List[FibTarget]:
    """
    After Wave 3 end, project likely Wave 4 retracement targets.
    """
    targets: List[FibTarget] = []
    for ratio, pct in [(0.236, "23.6"), (0.382, "38.2"), (0.500, "50.0")]:
        price = fib_retracement(p2.price, p3.price, ratio)
        targets.append(FibTarget(
            label=f"Wave 4 retracement: {pct}% of Wave 3",
            ratio=ratio,
            price=price,
            description=(
                f"Wave 4 may retrace to {price:.4f} "
                f"({pct}% of Wave 3)"
            ),
        ))
    return targets


def wave5_target(p0: Pivot, p1: Pivot, p2: Pivot, p3: Pivot,
                 p4: Pivot) -> List[FibTarget]:
    """
    After Wave 4 end, project likely Wave 5 targets.
    Wave 5 often equals Wave 1 in length, or is 61.8 % of W1–W3.
    """
    targets: List[FibTarget] = []
    w1_len = abs(p1.price - p0.price)
    net_w1_w3 = abs(p3.price - p0.price)
    bullish = p1.price > p0.price
    sign = 1 if bullish else -1

    # W5 = W1
    price_eq = p4.price + sign * w1_len
    targets.append(FibTarget(
        label="Wave 5 target: equal to Wave 1",
        ratio=1.000,
        price=price_eq,
        description=f"Wave 5 equal to Wave 1 → {price_eq:.4f}",
    ))

    # W5 = 61.8 % of net W1–W3 distance
    price_fib = p4.price + sign * net_w1_w3 * 0.618
    targets.append(FibTarget(
        label="Wave 5 target: 61.8% of W1-W3 net",
        ratio=0.618,
        price=price_fib,
        description=f"Wave 5 = 61.8% of W1–W3 net distance → {price_fib:.4f}",
    ))

    return targets


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANALYZER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ElliottWaveAnalyzer:
    """
    Detect and validate Elliott Wave patterns in OHLCV data.

    Parameters
    ----------
    data : dict or pandas.DataFrame
        Must contain 'high' and 'low' columns/keys (lists or Series).
    pivot_len : int
        Number of bars on each side used to confirm a swing pivot.
    """

    def __init__(self, data, pivot_len: int = 5):
        # Accept both dict and pandas DataFrame
        try:
            self.highs = list(data["high"])
            self.lows  = list(data["low"])
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "data must have 'high' and 'low' keys/columns"
            ) from exc

        self.pivot_len = pivot_len
        self._pivots: Optional[List[Pivot]] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self) -> dict:
        """
        Run the full Elliott Wave analysis.

        Returns
        -------
        dict with keys:
            pivots     : List[Pivot]
            waves      : List[WaveSequence]   – all detected sequences
            latest     : WaveSequence | None  – most recent valid sequence
            targets    : List[FibTarget]      – next-wave targets
            state      : str                  – current wave-count label
        """
        pivots  = self.pivots()
        waves   = self._detect_all_sequences(pivots)
        valid   = [w for w in waves if w.is_valid]
        latest  = valid[-1] if valid else None
        targets = self._compute_targets(pivots, latest)
        state   = self._summarize_state(latest, pivots)

        return {
            "pivots":  pivots,
            "waves":   waves,
            "valid":   valid,
            "latest":  latest,
            "targets": targets,
            "state":   state,
        }

    def pivots(self) -> List[Pivot]:
        """Return (and cache) all detected pivot points."""
        if self._pivots is None:
            self._pivots = find_pivots(self.highs, self.lows, self.pivot_len)
        return self._pivots

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _detect_all_sequences(
        self, pivots: List[Pivot]
    ) -> List[WaveSequence]:
        """
        Slide a window over all pivots and try to fit impulse (6 pivots)
        and corrective (4 pivots) patterns.
        """
        sequences: List[WaveSequence] = []

        # Try every 6-pivot window for impulse patterns
        for i in range(len(pivots) - 5):
            ps = pivots[i: i + 6]
            # Must alternate high/low
            if not self._alternates(ps):
                continue
            seq = self._try_impulse(ps)
            if seq:
                sequences.append(seq)

        # Try every 4-pivot window for ABC corrective patterns
        for i in range(len(pivots) - 3):
            ps = pivots[i: i + 4]
            if not self._alternates(ps):
                continue
            seq = self._try_abc(ps)
            if seq:
                sequences.append(seq)

        return sequences

    @staticmethod
    def _alternates(ps: List[Pivot]) -> bool:
        for i in range(len(ps) - 1):
            if ps[i].is_high == ps[i + 1].is_high:
                return False
        return True

    @staticmethod
    def _try_impulse(ps: List[Pivot]) -> Optional[WaveSequence]:
        p0, p1, p2, p3, p4, p5 = ps
        bullish = p1.price > p0.price

        passed, failed = validate_impulse(p0, p1, p2, p3, p4, p5)

        seq_type = "impulse_bull" if bullish else "impulse_bear"
        waves = [
            Wave("1", p0, p1, "impulse"),
            Wave("2", p1, p2, "corrective"),
            Wave("3", p2, p3, "impulse"),
            Wave("4", p3, p4, "corrective"),
            Wave("5", p4, p5, "impulse"),
        ]
        return WaveSequence(
            waves=waves,
            sequence_type=seq_type,
            rules_passed=passed,
            rules_failed=failed,
        )

    @staticmethod
    def _try_abc(ps: List[Pivot]) -> Optional[WaveSequence]:
        pA0, pA1, pB, pC = ps

        passed, failed = validate_abc(pA0, pA1, pB, pC)

        bullish_correction = pA0.price < pA1.price
        seq_type = "abc_bull" if bullish_correction else "abc_bear"
        waves = [
            Wave("A", pA0, pA1, "corrective"),
            Wave("B", pA1, pB,  "corrective"),
            Wave("C", pB,  pC,  "corrective"),
        ]
        return WaveSequence(
            waves=waves,
            sequence_type=seq_type,
            rules_passed=passed,
            rules_failed=failed,
        )

    def _compute_targets(
        self,
        pivots: List[Pivot],
        latest: Optional[WaveSequence],
    ) -> List[FibTarget]:
        """Generate Fibonacci targets based on the most recent wave state."""
        if not latest or len(pivots) < 4:
            return []

        seq_type = latest.sequence_type

        if seq_type in ("impulse_bull", "impulse_bear"):
            # After 5-wave impulse → ABC corrective targets
            w = latest.waves
            return impulse_targets_after_wave5(
                w[0].start, w[0].end,  # W1
                w[1].end,              # W2 end
                w[2].end,              # W3 end
                w[4].end,              # W5 end
            )

        if seq_type in ("abc_bull", "abc_bear"):
            # After ABC correction → next impulse Wave 1 targets
            w = latest.waves
            return corrective_targets_after_abc(
                w[0].start, w[0].end,  # A
                w[1].end,              # B end
                w[2].end,              # C end
            )

        return []

    @staticmethod
    def _summarize_state(
        latest: Optional[WaveSequence],
        pivots: List[Pivot],
    ) -> str:
        if latest is None:
            return "No valid Elliott Wave pattern detected yet."

        last_wave = latest.waves[-1]
        direction = last_wave.direction
        seq = latest.sequence_type

        if seq in ("impulse_bull", "impulse_bear"):
            return (
                f"5-wave impulse completed ({'bullish' if seq=='impulse_bull' else 'bearish'}). "
                f"Wave 5 ended at {last_wave.end.price:.4f}. "
                f"Expecting ABC corrective now."
            )

        if seq in ("abc_bull", "abc_bear"):
            return (
                f"ABC corrective completed ({'bullish' if seq=='abc_bull' else 'bearish'}). "
                f"Wave C ended at {last_wave.end.price:.4f}. "
                f"Expecting new 5-wave impulse now."
            )

        return "Pattern detected but not classified."


# ─────────────────────────────────────────────────────────────────────────────
# PRETTY-PRINT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def print_analysis(result: dict) -> None:
    """Print a formatted Elliott Wave analysis report to stdout."""
    SEP = "─" * 70

    print(SEP)
    print("ELLIOTT WAVE ANALYSIS REPORT")
    print(SEP)

    print(f"\nTotal pivots found  : {len(result['pivots'])}")
    print(f"Wave sequences      : {len(result['waves'])}")
    print(f"Valid sequences     : {len(result['valid'])}")
    print(f"\nCurrent State       : {result['state']}")

    if result["latest"]:
        lat = result["latest"]
        print(f"\nMost Recent Pattern : {lat.sequence_type}")
        print(f"  Waves:")
        for w in lat.waves:
            print(f"    {w}")
        print(f"  Rules PASSED:")
        for r in lat.rules_passed:
            print(f"    ✓ {r}")
        if lat.rules_failed:
            print(f"  Rules FAILED:")
            for r in lat.rules_failed:
                print(f"    ✗ {r}")

    if result["targets"]:
        print(f"\nFibonacci Targets (next wave):")
        for t in result["targets"]:
            print(f"  [{t.label}]  → {t.price:.4f}")
            print(f"    {t.description}")

    print(SEP)


# ─────────────────────────────────────────────────────────────────────────────
# QUICK DEMO  (run as script:  python elliott_wave.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Synthetic price data that forms a textbook bullish 5-wave impulse
    # followed by an ABC correction.
    # Prices: 100 → 120 → 112 → 145 → 130 → 155 → 140 → 135 → 145
    highs = [
        100, 102, 105, 108, 110, 112, 115, 118, 120,  # Wave 1 up
        119, 117, 115, 114, 112,                        # Wave 2 down
        115, 120, 125, 130, 135, 140, 145,              # Wave 3 up
        143, 141, 138, 135, 132, 130,                   # Wave 4 down
        132, 135, 138, 141, 145, 148, 150, 152, 155,   # Wave 5 up
        153, 150, 147, 144, 141, 140,                   # A down
        141, 143, 145, 146, 147,                        # B up
        146, 144, 142, 140, 138, 135,                   # C down
    ]
    lows = [h - 2 for h in highs]   # simple spread

    data = {"high": highs, "low": lows}

    analyzer = ElliottWaveAnalyzer(data, pivot_len=3)
    result   = analyzer.analyze()
    print_analysis(result)
