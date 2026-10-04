# Hypothesis registry

No hypothesis is a validated improvement. Machine-readable definitions, risks and
proposed tests live in `config/hypotheses.json`; the frontend reads that file.

Rank favors a plausible mechanism, evidence already collected, simple causal
inputs, potential to generalize, low flexibility and feasible prospective collection.
Ranks are research priorities, not estimated probabilities or a strategy score.

| Rank | ID | Direction | Main constraint |
| --- | --- | --- | --- |
| 1 | H4 | Volatility-conditioned quality | Larger rebounds also carry larger losses |
| 2 | H7 | Rebound duration | Validate existing ten-bar hold before adaptive timing |
| 3 | H10 | Relative-to-SPY severity | Absolute profit is not stock-specific edge |
| 4 | H2 | Falling-knife avoidance | Severe weakness can also precede stronger rebounds |
| 5 | H6 | Component quality | Correlation and small subgroups |
| 6 | H5 | Market regimes | Few independent regimes; raw and excess disagree |
| 7 | H3 | Confirmation entry | Later entry may miss rebound; execution must be causal |
| 8 | H8 | Rebound-path exit | Flexible rules invite search; daily order ambiguity |
| 9 | H9 | Stock characteristics | No winning-stock whitelist |
| 10 | H1 | Repeated support | Current recorded definition has unfavorable evidence |

Historical data is for hypothesis generation. A future candidate needs a separate
registration and frozen code/configuration before its first eligible signal. A
prospective archive written from historical replay remains retrospective.

See [EXP-005 proposal](EXP005_PROPOSAL.md), which has **not** been registered or run.
