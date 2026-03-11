# Elliott Wave Theory – Python Library & TradingView Indicator

Implementation of **all rules and conditions** from  
*SweeGlu – Practical Application of Elliott Wave Principle* (Chapters 1, 4, 7–14, 17–21).

## Contents

| File / Folder | Description |
|---|---|
| `elliott_wave/` | Python package – rules, patterns, Fibonacci |
| `elliott_wave_indicator.pine` | TradingView Pine Script v5 indicator |
| `tests/` | pytest test suite (58 tests) |

---

## Python Library

### Quick Start

```python
from elliott_wave import ElliottWaveAnalyzer

# 5-wave impulse pivots  [W0, W1, W2, W3, W4, W5]
pivots = [0.0, 70.0, 42.0, 170.0, 125.0, 200.0]

analyzer = ElliottWaveAnalyzer(pivots, bullish=True)
report   = analyzer.full_report()
print(report)
```

**Output (example)**

```
Pattern : Impulse
Valid   : True
Summary : Valid Impulse. Wave 5 qualifies. Alternation: NOT observed.

Rule Checks:
  [✓] Wave 5 Qualification: Wave 5 qualifies: ends beyond Wave 3 and achieves 58.6% …
  [✗] Alternation Principle: Alternation not observed …

Wave 5 / Next-Wave Targets:
  Wave5_38.2%: 173.9062
  Wave5_61.8%: 203.7344
  Wave5_100.0%: 253.0000
  Wave5_161.8%: 332.2234
```

### Corrective Wave Analysis

```python
from elliott_wave import ElliottWaveAnalyzer

# A-B-C pivots  [A_start, A_end, B_end, C_end]
pivots   = [200.0, 150.0, 172.0, 110.0]
analyzer = ElliottWaveAnalyzer(pivots, bullish=False)
report   = analyzer.analyze_correction()
print(report)
# trade_setup contains entry zone, stop loss, and targets for zigzag patterns
```

### Individual Rule Checks

```python
from elliott_wave.rules import (
    check_wave2_retrace,
    check_wave3_not_shortest,
    check_wave4_no_overlap,
    check_wave5_qualification,
    check_38pct_breakout,
    alternation_check,
)

# Chapter 1 – Basic Rules
r = check_wave2_retrace(wave1_start=100, wave1_end=200, wave2_end=150)
print(r.passed, r.reason)

r = check_wave3_not_shortest(0, 100, 80, 200, 160, 220)
print(r.passed)

r = check_wave4_no_overlap(wave1_end=200, wave4_end=210, bullish=True)
print(r.passed)

# Chapter 18 – 38% breakout trail stop
r = check_38pct_breakout(wave_start=100, wave_end=200, current_price=168, bullish=True)
print(r.passed, r.reason)
```

### Fibonacci Utilities

```python
from elliott_wave.fibonacci import (
    retracement_levels_for,
    projection_levels_for,
    retracement_price,
    projection_price,
)

# All retracement levels for a wave 100 → 200
levels = retracement_levels_for(100, 200)
# {'23.6%': 176.4, '38.2%': 161.8, '50.0%': 150.0, '61.8%': 138.2, ...}

# Wave 5 projection targets from Wave 4 end
targets = projection_levels_for(wave_start=60, wave_end=180, project_from=130)
# {'38.2%': 175.84, '61.8%': 204.16, '100.0%': 250.0, '161.8%': 323.76, ...}
```

### Pattern Detection

```python
from elliott_wave.patterns import (
    detect_zigzag,
    detect_irregular_correction,
    detect_flat_correction,
    detect_complex_correction,
    zigzag_trade_setup,
)

# Simple Zigzag (Chapter 10)
r = detect_zigzag(a_start=200, a_end=150, b_end=172, c_end=110, bullish=False)
print(r.passed, r.pattern)

# 38% retracement trade setup (Chapter 18)
setup = zigzag_trade_setup(200, 150, 172, 110, bullish=False)
print(setup)
# {'entry_zone': (low, high), 'stop_loss': ..., 'target_1': 172, 'target_2': 200}
```

---

## Rules Implemented

### Chapter 1 – Basic Rules
| Rule | Implemented |
|---|---|
| Wave 2 never retraces more than 100% of Wave 1 | ✓ `check_wave2_retrace` |
| Wave 3 can never be the shortest impulse wave | ✓ `check_wave3_not_shortest` |
| Wave 4 cannot overlap Wave 1 (diagonal exception) | ✓ `check_wave4_no_overlap` |

### Chapter 4 – Wave Personalities
| Rule | Implemented |
|---|---|
| Extended Wave 3: projects > 161.8% of Wave 1 | ✓ `classify_wave3` |
| Extended Wave 5: projects > 61.8% of Wave 3 | ✓ `classify_wave5` |
| Failed Wave 5: length < Wave 1 length | ✓ `classify_wave5` |

### Chapters 7-9 – Impulse Patterns
| Pattern | Implemented |
|---|---|
| Standard 5-wave Impulse | ✓ `detect_impulse` |
| Leading Diagonal (Wave 1, 3-3-3-3-3 substructure) | ✓ `detect_leading_diagonal` |
| Ending Diagonal (Wave 5, 3-3-3-3-3 substructure) | ✓ `detect_ending_diagonal` |

### Chapters 10-13 – Corrective Patterns
| Pattern | Implemented |
|---|---|
| Simple Zigzag (A impulse, B 38-61%, C > 100%) | ✓ `detect_zigzag` |
| Irregular Correction (B > 100% of A) | ✓ `detect_irregular_correction` |
| 3-3-5 Flat (B ≈ 100%, C < 100%) | ✓ `detect_flat_correction` |
| Complex Correction (5+ corrective waves) | ✓ `detect_complex_correction` |

### Chapters 2, 5 – Fibonacci
| Level / Ratio | Implemented |
|---|---|
| Retracement: 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100% | ✓ |
| Projection: 38.2%, 61.8%, 100%, 123.6%, 161.8%, 261.8% | ✓ |
| Wave 4 normal range: 23-38% of Wave 3 | ✓ |
| Alternation Principle (Wave 2 vs Wave 4 depth) | ✓ `alternation_check` |

### Chapters 14, 17-18 – Extensions, Failures & Trading
| Rule | Implemented |
|---|---|
| Wave 5 qualification (> W3 end, ≥ 38% projection) | ✓ `check_wave5_qualification` |
| 38% breakout confirmation / trail stop | ✓ `check_38pct_breakout` |
| Zigzag trade setup (entry zone, stop, targets) | ✓ `zigzag_trade_setup` |

---

## TradingView Pine Script

**File:** `elliott_wave_indicator.pine`  
**Version:** Pine Script v5

### How to Use
1. Open [TradingView](https://tradingview.com) and go to the **Pine Editor** (bottom panel).
2. Paste the full contents of `elliott_wave_indicator.pine`.
3. Click **Add to chart**.
4. Apply to **5–15 minute Nifty** (or any liquid instrument) chart for best results.

### Indicator Features
- **Pivot detection** with configurable lookback length.
- **Wave labels** (0-1-2-3-4-5) with colour-coded rule validation (green = valid, red = rule broken).
- **Extended Wave 3** flag when projection > 161.8%.
- **Wave 5 qualification** check shown in the info table.
- **Fibonacci retracement levels** for Waves 2 and 4.
- **Wave 5 projection targets** (38%, 61.8%, 100%, 161.8% of Wave 3 length).
- **38% breakout trail stop** and 23% hard stop levels (Chapter 18).
- **Background highlight** when Wave 3 is the active segment.
- **Info table** (top-right) showing all rule statuses and price levels.

### Settings
| Setting | Default | Description |
|---|---|---|
| Pivot Lookback Length | 5 | Bars each side to confirm a swing high/low |
| Show Fibonacci Levels | On | Show W2 and W4 retracement lines |
| Show Wave 5 Targets | On | Show projected W5 targets |
| Show 38% Trade Setup | On | Show entry / stop levels |

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

All 58 tests should pass.

---

## Practice Recommendation

> Apply on **5–15 minute Nifty** charts for faster learning.  
> Start by identifying clear **impulse patterns**, then progress to **corrective patterns**.  
> Use the 38% retracement level as a **trailing stop-loss** for positional trades.
