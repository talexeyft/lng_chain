import sqlite3
import pandas as pd
import os

DB_PATH = os.environ.get("DB_PATH", "ai_data/network_stats.db")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "ai_experiments/cell_traffic_comparison/results")

os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Compare top cells traffic between Nov 7 and Nov 9
query_7 = """
SELECT cellname, avg(cs_traffic) as avg_cs_nov7
FROM hour_stats
WHERE date(dt) = '2025-11-07' AND cs_traffic > 0
GROUP BY cellname ORDER BY avg_cs_nov7 DESC LIMIT 10
"""

query_9 = """
SELECT cellname, avg(cs_traffic) as avg_cs_nov9
FROM hour_stats
WHERE date(dt) = '2025-11-09' AND cs_traffic > 0
GROUP BY cellname ORDER BY avg_cs_nov9 DESC LIMIT 10
"""

df_7 = pd.read_sql_query(query_7, conn)
df_9 = pd.read_sql_query(query_9, conn)

# Merge on cellname
merged = df_7.merge(df_9, on='cellname', how='outer').fillna(0)

# Calculate delta
merged['delta'] = merged['avg_cs_nov9'] - merged['avg_cs_nov7']
merged['pct_change'] = (merged['delta'] / merged['avg_cs_nov7'] * 100).replace([float('inf'), -float('inf')], 0)

# Save to file
merged.round(2).to_csv(f"{OUTPUT_DIR}/cell_traffic_change.tsv", sep='\t', index=False)

# Identify cells with biggest drop
dropped = merged[merged['avg_cs_nov7'] > 0].sort_values('delta').head(5)
top_dropped = dropped[['cellname', 'avg_cs_nov7', 'avg_cs_nov9', 'delta', 'pct_change']]

# Print summary
print("Топ-5 ячеек с наибольшим падением трафика за период (07→09 ноября):")
print(top_dropped.to_string(index=False))

conn.close()
