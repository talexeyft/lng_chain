import sqlite3
import pandas as pd
import os

DB_PATH = os.environ.get("DB_PATH", "ai_data/network_stats.db")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "ai_experiments/cs_traffic_trend/results")

os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Voice traffic by day
query = """
SELECT date(dt) as date, sum(cs_traffic) as total_cs_traffic
FROM hour_stats
WHERE date(dt) >= '2025-11-07'
GROUP BY date(dt)
ORDER BY date(dt)
"""

df = pd.read_sql_query(query, conn)

# Day-over-day change
df['diff'] = df['total_cs_traffic'].diff()
df['pct_change'] = df['total_cs_traffic'].pct_change() * 100

# Save summary
summary = df.round(2)
summary.to_csv(f"{OUTPUT_DIR}/cs_traffic_changes.tsv", sep='\t', index=False)

# Print summary to stdout
print("Голосовой трафик по дням:")
print(summary.to_string(index=False))

# Detailed analysis of drop
print("\n\nАнализ падения трафика:")
prev_day = df.iloc[-2]['total_cs_traffic']
curr_day = df.iloc[-1]['total_cs_traffic']
drop_pct = df.iloc[-1]['pct_change']
print(f"- Падение с {prev_day:.2f} Эрл до {curr_day:.2f} Эрл")
print(f"- Снижение на {abs(drop_pct):.1f}% за день")

conn.close()
