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

Implementation clarification: time to positive MFE is undefined when the full
path has no positive favorable excursion. Twenty-five real paths have zero MFE;
they stay in the timing denominator rather than being mislabeled as a day-one
favorable opportunity. This corrects diagnostic indexing, not a strategy rule.

<!-- DIAGNOSIS_RESULTS_START -->
## Findings — exploratory, generated from verified artifacts

**No validated improvement emerged.** Positive raw rebounds coexist with weak
ticker-level SPY breadth. Exit choice changes risk as well as profit. More
components and repeated prior successful zones do not automatically help.

The recorded revisit group has 1249 complete ten-bar events: gross mean 0.761%, SPY excess -0.070%. The no-known-zone group has gross mean 1.179% and excess 0.359%. This definition does not support the original repeated-support intuition; it is not a reason to tune the zone.

### What the failure modes suggest

- Frequency alone does not establish that V1 is too permissive. EXP-002's condition/frequency rates remain unchanged.
- Exact component combinations differ, but the largest returns are not independent component effects. Some groups are small.
- Strong negative recent momentum is not uniformly worse: deeper dips can also rebound more. A falling-knife filter is not justified.
- High ATR events have larger rebound means **and deeper MAE**. This is a scale/risk relationship, not a free improvement.
- Below-SPY-average events have larger gross mean but lower excess and deeper MAE than above-average events. Regime filtering is unvalidated.
- High relative-volume events have weaker gross/excess means in this description. No volume filter follows.
- Next-open gaps vary with later outcomes, but are future information relative to the original signal. They cannot retroactively filter V1.
- Ticker-average ATR/volatility correlate with return and excess; survivor selection, sample size and market exposure remain confounders.
- EXP-004 isolates exit behavior on the same independent entries. Time-only EV is highest among the primary comparison, but tail risk prevents declaring it superior.
- EXP-001 roughly broke even after costs on its inspected holdout; EXP-002 failed its breadth criterion; EXP-003 exposed data/provenance limits. None is erased by later findings.

### Scorecard and what would count as stronger

Primary: net EV, paired SPY excess and consistency across chronological periods.
Secondary: median, win rate, average win/loss, profit factor, tail loss, ticker
drawdown, MFE capture and frequency. Robustness: positive folds/tickers, equal-ticker
median, concentration and parameter stability. There is no combined score.

Before any future test, define a risk budget and registered acceptable deterioration
relative to V1. A positive EV difference with worse downside is mixed evidence.
Review only at the original archive gates; insufficient fresh evidence remains pending.

<details><summary>Ten-bar groups — including unfavorable results</summary>

| analysis | group | completed | mean | median | excess | mfe | mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_events | all | 4652 | 1.066% | 0.728% | 0.244% | 5.433% | -4.594% |
| combination | ABC | 1305 | 1.560% | 1.178% | 0.337% | 5.883% | -4.450% |
| combination | ABCD | 1087 | 0.768% | 0.638% | 0.133% | 5.386% | -5.229% |
| combination | ABD | 255 | 1.836% | 1.453% | 0.614% | 6.344% | -4.546% |
| combination | ACD | 160 | 1.726% | 1.032% | 0.846% | 6.105% | -4.562% |
| combination | BCD | 1845 | 0.729% | 0.369% | 0.140% | 4.957% | -4.332% |
| dip_component_count | 3 | 3565 | 1.157% | 0.770% | 0.278% | 5.447% | -4.401% |
| dip_component_count | 4 | 1087 | 0.768% | 0.638% | 0.133% | 5.386% | -5.229% |
| regime | above | 3562 | 0.926% | 0.585% | 0.276% | 5.002% | -4.248% |
| regime | below | 1090 | 1.526% | 1.343% | 0.139% | 6.840% | -5.726% |
| support_group | no_known_successful_zone | 3403 | 1.179% | 0.787% | 0.359% | 5.541% | -4.535% |
| support_group | revisit | 1249 | 0.761% | 0.544% | -0.070% | 5.136% | -4.756% |
| component_presence | A active | 2807 | 1.288% | 0.958% | 0.312% | 5.745% | -4.767% |
| component_presence | A inactive | 1845 | 0.729% | 0.369% | 0.140% | 4.957% | -4.332% |
| component_presence | B active | 4492 | 1.043% | 0.723% | 0.222% | 5.409% | -4.596% |
| component_presence | B inactive | 160 | 1.726% | 1.032% | 0.846% | 6.105% | -4.562% |
| component_presence | C active | 4397 | 1.022% | 0.699% | 0.222% | 5.380% | -4.597% |
| component_presence | C inactive | 255 | 1.836% | 1.453% | 0.614% | 6.344% | -4.546% |
| component_presence | D active | 3347 | 0.874% | 0.564% | 0.207% | 5.257% | -4.651% |
| component_presence | D inactive | 1305 | 1.560% | 1.178% | 0.337% | 5.883% | -4.450% |
| return_5d | low | 1483 | 1.568% | 1.191% | 0.587% | 6.861% | -5.400% |
| return_5d | middle | 2897 | 0.848% | 0.535% | 0.112% | 4.741% | -4.166% |
| return_5d | high | 272 | 0.655% | 0.400% | -0.219% | 5.009% | -4.763% |
| return_5d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| atr_pct_14 | low | 1006 | 0.207% | 0.290% | -0.500% | 3.117% | -3.083% |
| atr_pct_14 | middle | 2888 | 0.955% | 0.710% | 0.167% | 5.140% | -4.406% |
| atr_pct_14 | high | 758 | 2.631% | 2.174% | 1.523% | 9.619% | -7.318% |
| atr_pct_14 | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| relative_volume_20d | low | 1750 | 1.178% | 0.753% | 0.409% | 5.416% | -4.502% |
| relative_volume_20d | middle | 2446 | 1.070% | 0.730% | 0.183% | 5.545% | -4.651% |
| relative_volume_20d | high | 456 | 0.615% | 0.613% | -0.066% | 4.895% | -4.645% |
| relative_volume_20d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| relative_return_10d | low | 2149 | 1.045% | 0.819% | 0.335% | 5.932% | -5.091% |
| relative_return_10d | middle | 2089 | 0.911% | 0.547% | 0.128% | 4.789% | -4.165% |
| relative_return_10d | high | 414 | 1.965% | 1.904% | 0.356% | 6.086% | -4.181% |
| relative_return_10d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| drawdown_change_5 | low | 1232 | 1.557% | 1.162% | 0.583% | 6.733% | -5.304% |
| drawdown_change_5 | middle | 2997 | 0.869% | 0.594% | 0.125% | 4.913% | -4.302% |
| drawdown_change_5 | high | 413 | 0.987% | 0.671% | 0.095% | 5.317% | -4.630% |
| drawdown_change_5 | unknown | 10 | 2.990% | 1.420% | 0.184% | 5.753% | -3.329% |
| benchmark_return_20d | low | 744 | 2.505% | 2.194% | 0.772% | 7.446% | -5.180% |
| benchmark_return_20d | middle | 1338 | 0.878% | 0.435% | 0.379% | 5.562% | -5.208% |
| benchmark_return_20d | high | 2570 | 0.748% | 0.553% | 0.021% | 4.782% | -4.105% |
| benchmark_return_20d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| benchmark_drawdown_20d | low | 247 | 3.429% | 3.286% | 1.048% | 8.230% | -4.083% |
| benchmark_drawdown_20d | middle | 723 | 1.688% | 1.236% | 0.311% | 6.774% | -5.739% |
| benchmark_drawdown_20d | high | 3682 | 0.786% | 0.530% | 0.177% | 4.982% | -4.404% |
| benchmark_drawdown_20d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| benchmark_volatility_20d | low | 2940 | 1.065% | 0.583% | 0.360% | 5.063% | -4.145% |
| benchmark_volatility_20d | middle | 1290 | 0.527% | 0.522% | -0.130% | 5.559% | -5.419% |
| benchmark_volatility_20d | high | 422 | 2.728% | 2.932% | 0.578% | 7.622% | -5.203% |
| benchmark_volatility_20d | unknown | 0 | undefined | undefined | undefined | undefined | undefined |
| entry_gap | low | 610 | 2.708% | 2.104% | 1.464% | 7.758% | -5.348% |
| entry_gap | middle | 3411 | 0.587% | 0.433% | -0.092% | 4.710% | -4.293% |
| entry_gap | high | 631 | 2.071% | 1.470% | 0.883% | 7.092% | -5.497% |
| entry_gap | unknown | 0 | undefined | undefined | undefined | undefined | undefined |

</details>

<details><summary>Forward-return horizons</summary>

| horizon | events | completed | mean | median | excess | mfe | mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4825 | 4800 | 0.038% | 0.039% | 0.011% | 1.385% | -1.418% |
| 3 | 4825 | 4763 | 0.261% | 0.166% | 0.013% | 2.709% | -2.578% |
| 5 | 4825 | 4741 | 0.504% | 0.449% | 0.100% | 3.649% | -3.337% |
| 10 | 4825 | 4652 | 1.066% | 0.728% | 0.244% | 5.433% | -4.594% |
| 20 | 4825 | 4433 | 2.167% | 1.475% | 0.594% | 8.163% | -6.162% |

</details>

<details><summary>Rebound timing</summary>

| metric | complete_paths | reached | fraction | median_bars_if_reached |
| --- | --- | --- | --- | --- |
| positive_close | 4652 | 4019 | 86.393% | 1 |
| time_to_mfe | 4652 | 4627 | 99.463% | 6 |
| reach_2pct | 4652 | 3398 | 73.044% | 2 |
| reach_5pct | 4652 | 1893 | 40.692% | 5 |
| reach_10pct | 4652 | 646 | 13.887% | 6 |

</details>

<details><summary>Ticker relationships</summary>

| feature | outcome | tickers | spearman |
| --- | --- | --- | --- |
| atr_pct_14 | mean | 74 | 0.398 |
| atr_pct_14 | excess | 74 | 0.456 |
| relative_volume_20d | mean | 74 | 0.048 |
| relative_volume_20d | excess | 74 | 0.138 |
| relative_return_10d | mean | 74 | -0.160 |
| relative_return_10d | excess | 74 | -0.253 |
| volatility_20d | mean | 74 | 0.392 |
| volatility_20d | excess | 74 | 0.451 |
| events_per_252 | mean | 74 | -0.105 |
| events_per_252 | excess | 74 | -0.175 |

</details>

<details><summary>Features of positive and nonpositive ten-bar outcomes</summary>

| group | completed | return_5d | drawdown_change_5 | atr_pct_14 | relative_volume_20d | relative_return_10d | entry_gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| positive_gross | 2590 | -4.209% | -3.582% | 3.028% | 1.279 | -4.857% | -0.044% |
| nonpositive_gross | 2062 | -4.034% | -3.496% | 2.888% | 1.319 | -5.033% | 0.042% |

</details>

Timing fractions include paths that never reached a level; conditional timing
medians include only those that did. MFE includes opportunity after earlier
policy exits. Overlap, adjusted vintages, survivorship and incomplete prior-zone
history prevent causal or prospective claims. Horizon counts differ due to censoring.

Diagnostic configuration SHA256: `0bddba29617cad4da1806264e50136c246e7460f9056c37c4727a7a355f87177`.
Reproduce: `python -m scripts.diagnose_research`, then `python -m scripts.report_research_diagnosis --write-doc`.
<!-- DIAGNOSIS_RESULTS_END -->
