# Research diagnosis

Historical patterns generate hypotheses. Only genuinely prospective records can
provide fresh validation. No rule or parameter changes are authorized here.

## Diagnostic definitions recorded before calculation

The exact definitions are in `config/research_diagnosis.json`. Use the frozen
EXP-002 universe and observations, plus hash-verified EXP-004 artifacts. Preserve
all tickers, losing groups, missing values and original exclusions.

- Components: describe their presence **within existing V1 events**, and the five
  possible exact three/four-component combinations. These are overlapping,
  correlated groups, not independent component-effect estimates.
- Falling knives: group by fixed signal-time momentum, ATR, relative weakness,
  volume and five-observation change in drawdown. Fixed boundaries are descriptive,
  not optimized; missing inputs form an explicit unknown group.
- Timing: inspect the ten-bar path starting at next open. First positive close
  measures time to positive return; first high reaching 2/5/10% measures an
  intraday opportunity, not an executable fill. First maximum high measures time
  to MFE. Require a complete path inside the original fold.
- Entry gap: next open / signal close - 1. This is known **after** the signal and
  cannot be a signal-time filter without a different registered entry protocol.
- Regimes: retain causal EXP-002 SPY 200-day labels; additionally describe fixed
  trailing SPY return, drawdown and volatility bands. No classifier is selected.
- Prior successful dip zone: a same-ticker V1 event in the preceding 365 calendar
  days, whose ten-bar path ended strictly before the current signal, and whose
  highest high reached 5% above its next-open entry. The current close must be
  within 2% of that prior signal's low. Count qualifying visits and their ages.
  Today’s adjusted vintage can revise old price zones. This is a research
  definition, not evidence that support exists; no grid or trading rule follows.
- Stock heterogeneity: descriptive ticker means and correlations with causal
  signal-time inputs. Unequal histories and small samples remain visible.

All new tables are exploratory on consumed historical data. No statistical or
causal claim follows from choosing a favorable subgroup. EXP-001 through EXP-004
remain unchanged. EXP-005 will be proposed separately and will not run here.
