import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Load data
df = pd.read_csv('/home/alex/code/lng_chain/ai_data/query_701c38b8.tsv', sep='\t', parse_dates=['dt'])

# Basic stats
print("=== Голосовой трафик по часам ===")
print(f"Диапазон дат: {df['dt'].min()} - {df['dt'].max()}")
print(f"Всего измерений: {len(df)}")
print(f"\nОсновные статистики по cs_traffic:")
print(df['total_cs_traffic'].describe())

# Daily aggregation
df['date'] = df['dt'].dt.date
daily_traffic = df.groupby('date')['total_cs_traffic'].sum().reset_index()
print("\n=== Суточный голосовой трафик (всего за сутки) ===")
print(daily_traffic)

# Peak and off-peak
df['hour'] = df['dt'].dt.hour
hourly_avg = df.groupby('hour')['total_cs_traffic'].mean().reset_index()
print("\n=== Средний часовой трафик по часам суток ===")
print(hourly_avg)

# Compare last 24h vs previous 24h
latest_ts = df['dt'].max()
last_24h = df[(df['dt'] >= latest_ts - pd.Timedelta(hours=24)) & (df['dt'] <= latest_ts)]
prev_24h = df[(df['dt'] >= latest_ts - pd.Timedelta(hours=48)) & (df['dt'] < latest_ts - pd.Timedelta(hours=24))]

last_24h_sum = last_24h['total_cs_traffic'].sum()
prev_24h_sum = prev_24h['total_cs_traffic'].sum()
change_24h = ((last_24h_sum - prev_24h_sum) / prev_24h_sum) * 100

print(f"\n=== Сравнение последних 24ч vs предыдущих 24ч ===")
print(f"Последние 24ч: {last_24h_sum:.2f} МЭрл")
print(f"Предыдущие 24ч: {prev_24h_sum:.2f} МЭрл")
print(f"Изменение: {change_24h:+.1f}%")

# Save results
os.makedirs('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/results', exist_ok=True)
df.to_csv('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/results/hourly_traffic.tsv', sep='\t', index=False)
daily_traffic.to_csv('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/results/daily_traffic.tsv', sep='\t', index=False)
hourly_avg.to_csv('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/results/hourly_avg.tsv', sep='\t', index=False)

# Plot 1: Hourly trend over time
plt.figure(figsize=(12, 6))
plt.plot(df['dt'], df['total_cs_traffic'], marker='o', markersize=3, linewidth=0.8, alpha=0.7)
plt.title('Голосовой трафик (cs_traffic) по часам')
plt.xlabel('Дата-время')
plt.ylabel('cs_traffic, МЭрл')
plt.grid(True)
plt.tight_layout()
plt.savefig('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/plots/hourly_trend.png', dpi=150)

# Plot 2: Daily comparison
plt.figure(figsize=(8, 5))
plt.bar(daily_traffic['date'].astype(str), daily_traffic['total_cs_traffic'], color='steelblue')
plt.title('Суточный голосовой трафик')
plt.xlabel('Дата')
plt.ylabel('cs_traffic за сутки, МЭрл')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/plots/daily_comparison.png', dpi=150)

# Plot 3: Hourly average profile
plt.figure(figsize=(10, 5))
plt.plot(hourly_avg['hour'], hourly_avg['total_cs_traffic'], marker='o', linewidth=2, markersize=6, color='darkred')
plt.title('Средний часовой профиль голосового трафика')
plt.xlabel('Час суток')
plt.ylabel('cs_traffic, МЭрл (среднее)')
plt.grid(True)
plt.xticks(range(0, 24, 2))
plt.tight_layout()
plt.savefig('/home/alex/code/lng_chain/ai_experiments/voice_traffic_trend/plots/hourly_profile.png', dpi=150)

print("\nГрафики сохранены.")
