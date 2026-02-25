import pandas as pd
import os

BASELINE_START = '2025-02-24'
BASELINE_END = '2025-03-08'
RECENT_START = '2026-02-17'
RECENT_END = '2026-02-23'
DATA_DIR = '/home/alex/code/lng_chain/ai_data'
OUTPUT_DIR = '/home/alex/code/lng_chain/ai_experiments/edrx_rca_baseline_median'

os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_DIR, 'network_stats.tsv'), sep='\t', parse_dates=['dt'])

# Baseline median
baseline = df[(df['dt'] >= BASELINE_START) & (df['dt'] <= BASELINE_END)]
baseline_median = baseline.groupby('ne')['pct_edrx'].median().reset_index()
baseline_median.columns = ['ne', 'baseline_median_pct_edrx']
baseline_median.to_csv(os.path.join(OUTPUT_DIR, 'baseline_median.tsv'), sep='\t', index=False)

# Recent median
recent = df[(df['dt'] >= RECENT_START) & (df['dt'] <= RECENT_END)]
recent_median = recent.groupby('ne')['pct_edrx'].median().reset_index()
recent_median.columns = ['ne', 'recent_median_pct_edrx']
recent_median.to_csv(os.path.join(OUTPUT_DIR, 'recent_median.tsv'), sep='\t', index=False)

# Join and compute delta
summary = baseline_median.merge(recent_median, on='ne')
summary['delta_pct'] = ((summary['recent_median_pct_edrx'] - summary['baseline_median_pct_edrx']) / summary['baseline_median_pct_edrx']) * 100
summary['abs_delta_pct'] = summary['delta_pct'].abs()
summary = summary.sort_values('delta_pct')

summary.to_csv(os.path.join(OUTPUT_DIR, 'summary.tsv'), sep='\t', index=False)

print(f'Baseline period: {BASELINE_START} to {BASELINE_END}')
print(f'Recent period: {RECENT_START} to {RECENT_END}')
print(f'Total cells: {summary.shape[0]}')
print(f'\nBaseline median stats:')
print(summary['baseline_median_pct_edrx'].describe())
print(f'\nRecent median stats:')
print(summary['recent_median_pct_edrx'].describe())
print(f'\nDelta stats:')
print(summary['delta_pct'].describe())

# Critical cells (drop >15%)
critical = summary[summary['delta_pct'] < -15]
print(f'\nCells with eDRX drop >15%: {critical.shape[0]}')
if not critical.empty:
    print(critical[['ne', 'baseline_median_pct_edrx', 'recent_median_pct_edrx', 'delta_pct']])
