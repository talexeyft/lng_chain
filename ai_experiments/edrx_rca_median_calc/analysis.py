import sqlite3
import os
import statistics

DATA_DIR = '/home/alex/code/lng_chain/ai_data'
OUTPUT_DIR = '/home/alex/code/lng_chain/ai_experiments/edrx_rca_median_calc'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

db_path = os.path.join(DATA_DIR, 'network_stats.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Загрузим все данные
cursor.execute("""
    SELECT ne, dt, pct_edrx 
    FROM network_stats 
    ORDER BY ne, dt
""")
rows = cursor.fetchall()
conn.close()

BASELINE_START = '2025-02-24'
BASELINE_END = '2025-03-08'
RECENT_START = '2026-02-17'
RECENT_END = '2026-02-23'

from collections import defaultdict

baseline_vals = defaultdict(list)
recent_vals = defaultdict(list)

for ne, dt, pct_edrx in rows:
    if BASELINE_START <= dt <= BASELINE_END:
        baseline_vals[ne].append(pct_edrx)
    elif RECENT_START <= dt <= RECENT_END:
        recent_vals[ne].append(pct_edrx)

# Вычислим медианы
baseline_median = {}
recent_median = {}

for ne, vals in baseline_vals.items():
    baseline_median[ne] = statistics.median(vals)

for ne, vals in recent_vals.items():
    recent_median[ne] = statistics.median(vals)

# Соберём summary
summary = []
for ne in sorted(baseline_median.keys()):
    b = baseline_median[ne]
    r = recent_median.get(ne, 0)
    delta_pct = ((r - b) / b) * 100 if b != 0 else 0
    summary.append((ne, b, r, delta_pct))

# Запись baseline_median.tsv
with open(os.path.join(OUTPUT_DIR, 'baseline_median.tsv'), 'w') as f:
    f.write('ne\tbaseline_median_pct_edrx\n')
    for ne, val in sorted(baseline_median.items()):
        f.write(f'{ne}\t{val:.10f}\n')

# Запись recent_median.tsv
with open(os.path.join(OUTPUT_DIR, 'recent_median.tsv'), 'w') as f:
    f.write('ne\trecent_median_pct_edrx\n')
    for ne, val in sorted(recent_median.items()):
        f.write(f'{ne}\t{val:.10f}\n')

# Запись summary.tsv
with open(os.path.join(OUTPUT_DIR, 'summary.tsv'), 'w') as f:
    f.write('ne\tbaseline_median_pct_edrx\trecent_median_pct_edrx\tdelta_pct\n')
    for ne, b, r, d in sorted(summary, key=lambda x: x[3]):
        f.write(f'{ne}\t{b:.10f}\t{r:.10f}\t{d:.4f}\n')

# Критические БС
critical = [(ne, b, r, d) for ne, b, r, d in summary if d < -15]
critical.sort(key=lambda x: x[3])

print(f'Baseline period: {BASELINE_START} to {BASELINE_END}')
print(f'Recent period: {RECENT_START} to {RECENT_END}')
print(f'Total cells: {len(baseline_median)}')
print(f'\nBaseline median stats:')
b_vals = list(baseline_median.values())
print(f'  min={min(b_vals):.2f}, max={max(b_vals):.2f}, mean={statistics.mean(b_vals):.2f}, median={statistics.median(b_vals):.2f}')

print(f'\nRecent median stats:')
r_vals = list(recent_median.values())
print(f'  min={min(r_vals):.2f}, max={max(r_vals):.2f}, mean={statistics.mean(r_vals):.2f}, median={statistics.median(r_vals):.2f}')

print(f'\nDelta stats:')
d_vals = [d for _, _, _, d in summary]
print(f'  min={min(d_vals):.2f}%, max={max(d_vals):.2f}%, mean={statistics.mean(d_vals):.2f}%, median={statistics.median(d_vals):.2f}%')

print(f'\nCells with eDRX drop >15%: {len(critical)}')
for ne, b, r, d in critical:
    print(f'  {ne}: baseline={b:.2f}, recent={r:.2f}, delta={d:.2f}%')

# Сохраняем critical list
with open(os.path.join(OUTPUT_DIR, 'critical_cells.tsv'), 'w') as f:
    f.write('ne\tbaseline_median_pct_edrx\trecent_median_pct_edrx\tdelta_pct\n')
    for ne, b, r, d in critical:
        f.write(f'{ne}\t{b:.10f}\t{r:.10f}\t{d:.4f}\n')
    f.write('\n')
