"""Render EXP-002 documentation from hash-verified result artifacts, without evaluation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd


def render_report(directory: Path) -> str:
    """Render compact experiment tables only from hash-verified machine artifacts."""
    metadata = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
    for filename, expected in metadata['artifact_sha256'].items():
        if sha256((directory / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Artifact hash mismatch: {filename}')
    def read(name):
        return pd.read_csv(directory / f'{name}.csv', float_precision='round_trip')
    def pct(value):
        return 'undefined' if pd.isna(value) else f'{100 * value:.3f}%'
    def num(value):
        return 'undefined' if pd.isna(value) else f'{value:.3f}'
    def interval(row):
        return 'undefined' if pd.isna(row['ci_lower']) else f"[{pct(row['ci_lower'])}, {pct(row['ci_upper'])}]"
    lines = ['### EXP-002 results generated from verified artifacts', '',
             f"Execution revision: `{metadata['code_commit']}`; dirty tree: `{metadata['working_tree_dirty']}`.",
             f"Registered in `{metadata['preregistration_commit']}`; configuration SHA-256:",
             f"`{metadata['config_sha256']}`.", '',
             f"Requested {metadata['requested_count']}; usable {metadata['usable_count']}; excluded {metadata['excluded_count']}.",
             'Current-constituent static universe; all retained outcomes are reported without parameter selection.', '']
    def table(title, headers, rows):
        lines.extend([f'#### {title}', '', '| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'])
        lines.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)
        lines.append('')
    frequency, folds = read('frequency'), read('folds')
    fsum = read('frequency_fold').set_index('fold')
    rows = []
    for fold in folds.to_dict('records'):
        label = fold['fold']
        stats = fsum.loc[label]
        count = frequency.loc[(frequency.fold == label) & (frequency.ready > 0)].ticker.nunique()
        rows.append([label, fold['history_end'], fold['test_start'], fold['test_end'], count,
                     int(stats['ready']), int(stats['events']), pct(stats['condition_fraction_ready']),
                     num(stats['events_per_252_ready'])])
    table('Expanding folds and signal frequency', ['Fold', 'History end', 'OOS start', 'OOS end',
          'Ready tickers', 'Ready rows', 'Events', 'Condition / ready', 'Events / 252 ready'], rows)
    lines.extend([f"All folds share history origin {metadata['folds'][0]['history_start']}. The final fold may be partial. Readiness counts",
                  'include warm-up/history restrictions; no-event and absent ticker-folds remain in frequency.csv.', ''])
    forward = read('fold_summary')
    rows = []
    for row in forward.loc[forward.selection == 'events'].to_dict('records'):
        rows.append([row['fold'], row['horizon'], row['count'], row['excluded'], pct(row['mean']),
                     pct(row['median']), pct(row['average_mfe']), pct(row['average_mae']), interval(row)])
    table('All fixed-horizon event outcomes by fold (gross)', ['Fold', 'Bars', 'N', 'Excluded',
          'Mean', 'Median', 'MFE', 'MAE', '95% mean CI'], rows)
    rows = []
    for fold in folds.fold:
        selected = forward.loc[(forward.fold == fold) & (forward.horizon == 10)].set_index('selection')
        event = selected.loc['events']
        rows.append([fold, pct(event['mean']), pct(selected.loc['eligible', 'mean']),
                     pct(selected.loc['non_signal', 'mean']), pct(event['benchmark_mean']),
                     pct(event['mean_excess_return'])])
    table('Ten-bar baseline comparisons by fold', ['Fold', 'Event', 'Unconditional', 'Non-signal',
          'Matched SPY', 'Event minus SPY'], rows)
    pooled = read('oos_summary')
    rows = []
    for horizon in (1, 3, 5, 10, 20):
        group = pooled.loc[pooled.horizon == horizon].set_index('selection')
        row = group.loc['events']
        rows.append([horizon, int(row['count']), pct(row['mean']), pct(row['median']),
                     pct(group.loc['eligible', 'mean']), pct(group.loc['non_signal', 'mean']),
                     pct(row['benchmark_mean']), pct(row['mean_excess_return']), interval(row)])
    table('Pooled OOS event and baseline results', ['Bars', 'N', 'Event mean', 'Median', 'Unconditional',
          'Non-signal', 'Matched SPY', 'Excess', '95% event-mean CI'], rows)
    table('Pooled event excursions and dispersion', ['Bars', 'MFE', 'MAE', 'Std', 'Win rate'],
          [[r['horizon'], pct(r['average_mfe']), pct(r['average_mae']), pct(r['std']), pct(r['win_rate'])]
           for r in pooled.loc[pooled.selection == 'events'].to_dict('records')])
    rows = []
    trades = pd.concat([read('trade_fold_summary'), read('trade_oos_summary').assign(fold='all')])
    for row in trades.to_dict('records'):
        exits = [round(row[k] * row['trade_count']) for k in ('take_profit_rate', 'stop_loss_rate', 'time_exit_rate')]
        rows.append([row['fold'], row['mode'], row['trade_count'], pct(row['average_gross_return']),
                     pct(row['average_return']), pct(row['median_return']), pct(row['win_rate']),
                     num(row['profit_factor']), num(row['average_holding_bars']), '/'.join(map(str, exits))])
    table('Frozen barrier outcomes, including costs', ['Fold', 'Mode', 'N', 'Gross mean', 'Net mean',
          'Net median', 'Win rate', 'PF', 'Holding bars', 'TP/SL/time counts'], rows)
    lines.extend(['Costs are 1 bp commission plus 5 bp slippage per side. These are pooled trade statistics,',
                  'not allocated portfolio returns; no pooled Sharpe, Sortino or portfolio drawdown is claimed.', ''])
    distributions = read('distribution')
    rows = []
    for row in distributions.loc[distributions.kind != 'frequency'].to_dict('records'):
        rows.append([row['kind'], row['horizon'], row['metric'], row['positive_count'], row['negative_count'],
                     row['zero_count'], row['undefined_count'], pct(row['median']),
                     pct(row['q25']) + ' / ' + pct(row['q75']), pct(row['positive_fraction_defined'])])
    table('Cross-sectional distribution (requested-ticker accounting)', ['Kind', 'Bars', 'Metric', 'Positive',
          'Negative', 'Zero', 'Undefined', 'Median', 'Q25 / Q75', 'Positive / defined'], rows)
    observed = frequency.groupby('ticker').agg(events=('events', 'sum'), ready=('ready', 'sum'))
    usable = observed.loc[observed.ready > 0, 'events']
    exposures = frequency.loc[frequency.ready > 0, 'events_per_252_ready']
    lines.extend([f"Across usable tickers: events total median {usable.median():.1f}, Q25/Q75 "
                  f"{usable.quantile(.25):.1f}/{usable.quantile(.75):.1f}, min/max {usable.min()}/{usable.max()}.",
                  f"Across ready ticker-years (partial years included), events per 252 ready rows median "
                  f"{exposures.median():.3f}, Q25/Q75 {exposures.quantile(.25):.3f}/{exposures.quantile(.75):.3f}.", ''])
    table('Performance concentration (equal-notional return sums)', ['Measure', 'Positive sum', 'Negative sum',
          'Net sum', 'Top-five positive share', 'Top-five absolute share', 'Top positive contributors'],
          [[name, num(c['positive_sum']), num(c['negative_sum']), num(c['total_sum']),
            pct(c['top5_positive_share']), pct(c['top5_absolute_share']), ', '.join(c['top5_positive_tickers'])]
           for name, c in metadata['concentration'].items()])
    ticker = read('trade_ticker_summary')
    ticker = ticker.loc[ticker['mode'] == 'non_overlapping'].sort_values('ticker')
    table('Ticker non-overlapping barrier results (all candidate tickers retained)', ['Ticker', 'Trades', 'Net mean', 'Net median', 'PF'],
          [[r['ticker'], r['trade_count'], pct(r['average_return']), pct(r['median_return']), num(r['profit_factor'])]
           for r in ticker.to_dict('records')])
    regimes = read('regime_summary')
    rows = []
    for row in regimes.loc[regimes.selection == 'events'].to_dict('records'):
        control = regimes.loc[(regimes.regime == row['regime']) & (regimes.horizon == row['horizon'])
                              & (regimes.selection == 'eligible')].iloc[0]
        rows.append([row['regime'], row['horizon'], row['count'], pct(row['mean']), pct(control['mean']),
                     pct(row['benchmark_mean']), pct(row['mean_excess_return']), interval(row)])
    table('SPY 200-day-average regimes: pooled event outcomes', ['Regime', 'Bars', 'N', 'Event mean',
          'Unconditional', 'Matched SPY', 'Excess', '95% event-mean CI'], rows)
    table('Regime barrier outcomes', ['Regime', 'Mode', 'Trades', 'Net mean', 'Win rate', 'PF'],
          [[r['regime'], r['mode'], r['trade_count'], pct(r['average_return']), pct(r['win_rate']), num(r['profit_factor'])]
           for r in read('trade_regime_summary').to_dict('records')])
    table('Ten-bar component subgroups (descriptive)', ['Components', 'N', 'Mean', 'Median', '95% mean CI'],
          [[r['dip_component_count'], r['count'], pct(r['mean']), pct(r['median']), interval(r)]
           for r in read('component_oos_summary').to_dict('records')])
    excluded = read('exclusions')
    failures = excluded.loc[(excluded.fold == 'all') & (excluded.reason != 'previously_inspected_issuer')]
    table('Data/history exclusions (no replacement stocks)', ['Ticker', 'Reason', 'Detail'],
          failures[['ticker', 'reason', 'detail']].itertuples(index=False, name=None))
    lines.extend(['All per-fold regimes, per-ticker horizons and controls, audit statuses and missing-history',
                  'ticker-folds are retained in the machine-readable artifacts. Mean intervals do not test',
                  'event-minus-baseline differences. Source membership, adjusted prices, daily fills,',
                  'data exclusions, dependent samples and uncalibrated costs limit interpretation.', ''])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=Path('results/exp_002'))
    parser.add_argument('--check-doc', type=Path, help='Verify the generated block in an existing document')
    args = parser.parse_args()
    rendered = render_report(args.results_dir)
    if args.check_doc:
        document = args.check_doc.read_text(encoding='utf-8')
        saved = document.split('<!-- EXP002_GENERATED_TABLES_START -->', 1)[1].split(
            '<!-- EXP002_GENERATED_TABLES_END -->', 1)[0]
        if saved.strip() != rendered.strip():
            raise ValueError('Document tables differ from the verified artifacts')
        print('EXP-002 document tables match the hash-verified artifacts.')
    else:
        print(rendered)


if __name__ == '__main__':
    main()
