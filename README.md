# Elliott Wave Complete — TradingView Pine Script v5 Indicator

A comprehensive, rules-based **Elliott Wave** indicator for TradingView that automatically detects and labels impulse waves (1–2–3–4–5), corrective waves (A–B–C), sub-waves, Fibonacci levels, and projects the next probable move — all validated against the three hard Elliott Wave rules.

---

## 🚀 Quick Start

1. Open TradingView → Pine Script Editor (bottom panel)
2. Delete any existing code in the editor
3. Copy the full contents of [`elliott_wave_indicator.pine`](./elliott_wave_indicator.pine)
4. Paste into the editor and click **Add to chart**
5. Tune inputs in the **Settings → Inputs** panel

> **Recommended timeframes:** 15m / 1H for Nifty & Bank Nifty, 1H / 4H for Forex/Crypto

---

## 📐 Elliott Wave Rules Enforced

| # | Rule | Description |
|---|------|-------------|
| 1 | **Wave 2 Rule** | Wave 2 must *never* retrace more than 100% of Wave 1 |
| 2 | **Wave 3 Rule** | Wave 3 must *never* be the shortest of Waves 1, 3, and 5 |
| 3 | **Wave 4 Rule** | Wave 4 must *never* overlap the price territory of Wave 1 |

Each rule is validated in real-time. Failing waves are **highlighted in red**. The dashboard table shows pass/fail for all three rules.

---

## 🌊 What Is Drawn on the Chart

| Element | Description |
|---------|-------------|
| **① ② ③ ④ ⑤** labels | Impulse wave pivots (green/lime = valid, red = rule violation) |
| **Ⓐ Ⓑ Ⓒ** labels | Corrective (A-B-C) wave pivots |
| **• dots** | Sub-wave pivots at a finer degree |
| **Connecting lines** | Solid coloured lines linking each wave pivot |
| **Fibonacci dashed lines** | 23.6% / 38.2% / 50% / 61.8% / 78.6% retracements from W5 |
| **Fibonacci dotted lines** | 100% / 127.2% / 161.8% / 200% / 261.8% extensions |
| **Green box** | Prediction zone — 38.2%–61.8% correction target for next move |
| **Wave 3 background** | Subtle green background highlights Wave 3 bars |
| **Dashboard table** | Top-right summary of wave count, degree, rules, and bias |

---

## ⚙️ Input Reference

### Pivot Detection

| Input | Default | Description |
|-------|---------|-------------|
| Pivot Length (main) | 5 | Bars left/right to confirm a swing pivot. Increase on noisy charts. |
| Sub-wave Pivot Length | 2 | Smaller lookback for sub-degree wave dots |
| Show Sub-waves | ✅ | Toggle sub-wave dot overlay |

### Wave Display

| Input | Default | Description |
|-------|---------|-------------|
| Show Impulse Waves | ✅ | Draw 1–2–3–4–5 labels and lines |
| Show Corrective Waves | ✅ | Draw A–B–C labels and lines |
| Show Fibonacci Levels | ✅ | Draw retracement / extension lines |
| Show Prediction Zone | ✅ | Draw next-move target box |
| Show Dashboard Table | ✅ | Show top-right info table |
| Draw Wave Connecting Lines | ✅ | Connect wave pivots with coloured lines |

### Wave Degree

| Input | Default | Options |
|-------|---------|---------|
| Wave Degree Mode | Auto (by Timeframe) | Auto (by Timeframe) / Manual |
| Manual Degree | Primary | Grand Supercycle, Supercycle, Cycle, Primary, Intermediate, Minor, Minute, Minuette, Sub-Minuette |

**Auto mode** automatically selects the degree based on the chart timeframe:

| Timeframe | Auto Degree |
|-----------|-------------|
| Monthly + | Grand Supercycle |
| Weekly | Supercycle |
| Daily | Cycle |
| 4H | Primary |
| 1H | Intermediate |
| 15m | Minor |
| 5m | Minute |
| 1m | Minuette |
| < 1m | Sub-Minuette |

---

## 🔔 Alert Conditions

Four built-in alert conditions can be enabled from *Alert → Condition*:

| Alert | Trigger |
|-------|---------|
| New High Pivot (Wave 1/3/5) | Confirmed swing high (main pivot length) |
| New Low Pivot (Wave 2/4) | Confirmed swing low (main pivot length) |
| Sub-wave High Pivot | Confirmed sub-degree swing high |
| Sub-wave Low Pivot | Confirmed sub-degree swing low |

---

## 🧠 How the Indicator Works

### 1. ZigZag Engine
The script detects confirmed pivot highs and lows using `ta.pivothigh()` / `ta.pivotlow()` and maintains a rolling array of the 20 most recent swings, merging consecutive same-direction pivots to produce a clean alternating ZigZag.

### 2. Impulse Wave Detection
Working backwards through the ZigZag array, the script finds the most recent 6-point alternating sequence (W0…W5) and validates it against all three Elliott Wave rules.

### 3. Corrective Wave Detection
After identifying the impulse, the script looks for a 3-point alternating sequence (A-B-C) following the impulse end.

### 4. Fibonacci Projection
- **Retracements** are drawn from W5 back toward W0 to show potential correction targets.
- **Extensions** are projected beyond W5 to show where the next impulse could reach.

### 5. Prediction Zone
A shaded box is drawn in the 38.2%–61.8% retracement zone of the most recent impulse — this is statistically the most common area where the corrective (A-B-C) wave terminates before the next impulse begins.

---

## 📊 Tips for Best Results

- **Zoom out** on the chart to see more bars and give the pivot detection room to work
- **Adjust Pivot Length** (3–8) to match the chart's volatility:
  - Noisy / volatile charts → higher values (6–10)
  - Smooth trending charts → lower values (3–5)
- **Use higher timeframes** (1H+) for cleaner wave structures
- Check the **Dashboard Table** to confirm all three rules pass before acting on a wave count
- The **Prediction Zone** is a *probability zone*, not a guaranteed target

---

## 📁 File Structure

```
mitesh/
├── elliott_wave_indicator.pine   # Pine Script v5 — paste into TradingView
└── README.md                     # This file
```

---

## 📜 Elliott Wave Degree Hierarchy

```
Grand Supercycle  (decades)
  └── Supercycle  (years)
        └── Cycle  (months–years)
              └── Primary  (weeks–months)
                    └── Intermediate  (days–weeks)
                          └── Minor  (hours–days)
                                └── Minute  (minutes–hours)
                                      └── Minuette  (minutes)
                                            └── Sub-Minuette
```

---

*Built for educational and analytical purposes. Always combine wave analysis with other confirmation tools before making trading decisions.*