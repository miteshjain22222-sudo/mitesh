# Elliott Wave Analyzer

Rules-based Elliott Wave analysis in Python, plus a ready-to-paste TradingView Pine Script indicator.

---

## Files

| File | Purpose |
|------|---------|
| `elliott_wave_analyzer.py` | Pure-Python Elliott Wave engine |
| `elliott_wave_indicator.pine` | TradingView Pine Script v5 indicator |
| `test_elliott_wave_analyzer.py` | 53 unit tests (pytest) |

---

## Elliott Wave Rules Implemented

### Impulse Wave (1-2-3-4-5)
| Rule | Description |
|------|-------------|
| **Rule 1** | Wave 2 never retraces more than **100%** of Wave 1 |
| **Rule 2** | Wave 3 is **never the shortest** motive wave among Waves 1, 3 and 5 |
| **Rule 3** | Wave 4 never enters the price territory of Wave 1 |

### Corrective Wave (A-B-C)
| Guideline | Description |
|-----------|-------------|
| Wave B | Retraces between **23.6% and 100%** of Wave A |
| Wave C | Typically at least **61.8%** of Wave A |

### Fibonacci Levels
- **Retracements:** 23.6%, 38.2%, 50.0%, 61.8%, 78.6%, 100%
- **Extensions:** 100%, 127.2%, 141.4%, 161.8%, 200%, 261.8%

---

## Python Usage

```python
from elliott_wave_analyzer import ElliottWaveAnalyzer

# Pass a list of closing prices (oldest first)
prices = [100, 105, 102, 115, 110, 128, 122, 125, 119, 130]

analyzer = ElliottWaveAnalyzer(prices, left_bars=3, right_bars=3)
count    = analyzer.analyze()

# Human-readable summary
print(count.summary())

# Next wave targets
for target in count.targets:
    print(target)

# JSON export (for integration with other systems)
print(analyzer.to_json())
```

### `ElliottWaveAnalyzer` parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prices` | — | `List[float]` of closing prices, oldest first |
| `left_bars` | `3` | Bars to the left required to confirm a pivot |
| `right_bars` | `3` | Bars to the right required to confirm a pivot |

**Tip:** Lower `left_bars`/`right_bars` values (e.g. 2) detect more pivots on noisy data; higher values (e.g. 5–10) produce fewer, more significant pivots.

### Key return types

```
WaveCount
  .waves          → List[Wave]         – confirmed waves
  .wave_type      → WaveType           – IMPULSE | CORRECTIVE | UNKNOWN
  .direction      → WaveDirection      – UP | DOWN | UNKNOWN
  .is_complete    → bool               – True when all 5 (or 3) waves found
  .is_valid       → bool               – True when no rule violations
  .next_wave_label→ str | None         – "1"–"5" or "A"/"B"/"C"
  .targets        → List[WaveTarget]   – Fibonacci price targets for next wave
  .violations     → List[str]          – rule violation messages
```

---

## TradingView Pine Script

1. Open **TradingView** → **Pine Script Editor** (bottom panel)
2. Click **"Open"** → **"New indicator"**
3. **Select all** existing code and **delete** it
4. **Paste** the entire contents of `elliott_wave_indicator.pine`
5. Click **"Add to chart"**

### What the indicator draws

| Element | Description |
|---------|-------------|
| ▲ / ▼ markers | Confirmed pivot highs / lows |
| Numbered lines ①–⑤ | Current 5-wave impulse count |
| Circled letters Ⓐ Ⓑ Ⓒ | Current A-B-C corrective count |
| Dashed horizontal lines | Fibonacci retracement grid on Wave 3 |
| Target labels (right of price) | Projected Wave 5 / Wave C targets |
| ⚠ banner | Shown when an Elliott rule is violated |

### Configurable inputs

| Input | Default | Description |
|-------|---------|-------------|
| Pivot Bars Left | 5 | Confirmation bars to the left of a pivot |
| Pivot Bars Right | 5 | Confirmation bars to the right of a pivot |
| Show Impulse Waves | ✓ | Toggle 1-2-3-4-5 labels |
| Show Corrective Waves | ✓ | Toggle A-B-C labels |
| Show Fibonacci Levels | ✓ | Toggle retracement grid |
| Show Next Wave Targets | ✓ | Toggle extension target labels |
| Show Rule Violations | ✓ | Toggle violation banner |

---

## Running the tests

```bash
pip install pytest
python -m pytest test_elliott_wave_analyzer.py -v
```

Expected output: **53 passed**