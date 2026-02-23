import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
import os

# Подключение к базе данных
conn = sqlite3.connect('/home/alex/code/lng_chain/ai_data/network_stats.db')

# Запрос данных за последние 14 дней
query = """
SELECT dt, ne, traffic_cs, traffic_ps, pct_edrx, drop_rate, latency_ms, cell_load, rrc_conn, dl_mbps, ul_mbps, prb_util
FROM network_stats
WHERE ne IN ('bs-22', 'bs-15', 'bs-62', 'bs-98', 'bs-73')
  AND dt >= date('now', '-14 days')
ORDER BY dt, ne
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Вычисление общего трафика (CS+PS)
df['total_traffic'] = df['traffic_cs'] + df['traffic_ps']

# Группировка по БС для расчета статистик
results = {}

for ne in df['ne'].unique():
    df_ne = df[df['ne'] == ne].sort_values('dt')
    
    # Средние значения
    mean_traffic_cs = df_ne['traffic_cs'].mean()
    mean_traffic_ps = df_ne['traffic_ps'].mean()
    mean_total_traffic = df_ne['total_traffic'].mean()
    mean_pct_edrx = df_ne['pct_edrx'].mean()
    mean_drop_rate = df_ne['drop_rate'].mean()
    mean_latency = df_ne['latency_ms'].mean()
    mean_cell_load = df_ne['cell_load'].mean()
    mean_rrc_conn = df_ne['rrc_conn'].mean()
    mean_dl_mbps = df_ne['dl_mbps'].mean()
    mean_ul_mbps = df_ne['ul_mbps'].mean()
    mean_prb_util = df_ne['prb_util'].mean()
    
    # Медианные значения
    median_traffic_cs = df_ne['traffic_cs'].median()
    median_traffic_ps = df_ne['traffic_ps'].median()
    median_total_traffic = df_ne['total_traffic'].median()
    median_pct_edrx = df_ne['pct_edrx'].median()
    median_drop_rate = df_ne['drop_rate'].median()
    median_latency = df_ne['latency_ms'].median()
    median_cell_load = df_ne['cell_load'].median()
    median_rrc_conn = df_ne['rrc_conn'].median()
    median_dl_mbps = df_ne['dl_mbps'].median()
    median_ul_mbps = df_ne['ul_mbps'].median()
    median_prb_util = df_ne['prb_util'].median()
    
    # Минимальные и максимальные значения
    min_total_traffic = df_ne['total_traffic'].min()
    max_total_traffic = df_ne['total_traffic'].max()
    
    # Доля CS от общего трафика
    mean_pct_cs = (df_ne['traffic_cs'] / df_ne['total_traffic'] * 100).mean()
    median_pct_cs = (df_ne['traffic_cs'] / df_ne['total_traffic'] * 100).median()
    
    results[ne] = {
        'mean_traffic_cs': mean_traffic_cs,
        'median_traffic_cs': median_traffic_cs,
        'mean_traffic_ps': mean_traffic_ps,
        'median_traffic_ps': median_traffic_ps,
        'mean_total_traffic': mean_total_traffic,
        'median_total_traffic': median_total_traffic,
        'mean_pct_edrx': mean_pct_edrx,
        'median_pct_edrx': median_pct_edrx,
        'mean_drop_rate': mean_drop_rate,
        'median_drop_rate': median_drop_rate,
        'mean_latency': mean_latency,
        'median_latency': median_latency,
        'mean_cell_load': mean_cell_load,
        'median_cell_load': median_cell_load,
        'mean_rrc_conn': mean_rrc_conn,
        'median_rrc_conn': median_rrc_conn,
        'mean_dl_mbps': mean_dl_mbps,
        'median_dl_mbps': median_dl_mbps,
        'mean_ul_mbps': mean_ul_mbps,
        'median_ul_mbps': median_ul_mbps,
        'mean_prb_util': mean_prb_util,
        'median_prb_util': median_prb_util,
        'min_total_traffic': min_total_traffic,
        'max_total_traffic': max_total_traffic,
        'mean_pct_cs': mean_pct_cs,
        'median_pct_cs': median_pct_cs,
    }

# Определяем 5 БС с самым низким трафиком по среднему значению
sorted_bss = sorted(results.keys(), key=lambda x: results[x]['mean_total_traffic'])

# Запись результатов в файл
output_dir = Path('/home/alex/code/lng_chain/ai_experiments/low_traffic_analysis')
output_dir.mkdir(parents=True, exist_ok=True)
results_file = output_dir / 'results' / 'summary_stats.tsv'
results_file.parent.mkdir(parents=True, exist_ok=True)

with open(results_file, 'w') as f:
    f.write("БС\tСредний трафик\tМедианный трафик\tСредний CS\tМедианный CS\tСредний PS\tМедианный PS\tДоля CS (средняя)\tДоля CS (медианная)\tDrop rate (сред)\tDrop rate (медиан)\tLatency (сред)\tLatency (медиан)\tCell load (сред)\tCell load (медиан)\tRRC conn (сред)\tRRC conn (медиан)\tDL Mbps (сред)\tDL Mbps (медиан)\tUL Mbps (сред)\tUL Mbps (медиан)\tPRB Util (сред)\tPRB Util (медиан)\tMin трафик\tMax трафик\n")
    
    for ne in sorted_bss:
        r = results[ne]
        f.write(f"{ne}\t{r['mean_total_traffic']:.2f}\t{r['median_total_traffic']:.2f}\t{r['mean_traffic_cs']:.2f}\t{r['median_traffic_cs']:.2f}\t{r['mean_traffic_ps']:.2f}\t{r['median_traffic_ps']:.2f}\t{r['mean_pct_cs']:.2f}\t{r['median_pct_cs']:.2f}\t{r['mean_drop_rate']:.2f}\t{r['median_drop_rate']:.2f}\t{r['mean_latency']:.2f}\t{r['median_latency']:.2f}\t{r['mean_cell_load']:.2f}\t{r['median_cell_load']:.2f}\t{r['mean_rrc_conn']:.2f}\t{r['median_rrc_conn']:.2f}\t{r['mean_dl_mbps']:.2f}\t{r['median_dl_mbps']:.2f}\t{r['mean_ul_mbps']:.2f}\t{r['median_ul_mbps']:.2f}\t{r['mean_prb_util']:.2f}\t{r['median_prb_util']:.2f}\t{r['min_total_traffic']:.2f}\t{r['max_total_traffic']:.2f}\n")

# Анализ аномалий
anomalies = []
for ne in results:
    df_ne = df[df['ne'] == ne].sort_values('dt')
    
    # Drop rate аномалии (среднее + 2 stddev)
    mean_drop = df_ne['drop_rate'].mean()
    std_drop = df_ne['drop_rate'].std()
    drop_anomalies = df_ne[df_ne['drop_rate'] > mean_drop + 2 * std_drop]
    if len(drop_anomalies) > 0:
        anomalies.append(f"{ne}: аномально высокий drop_rate (среднее {mean_drop:.2f}%, stddev {std_drop:.2f}%), пик {df_ne['drop_rate'].max():.2f}%")
    
    # Cell load аномалии
    mean_cell = df_ne['cell_load'].mean()
    std_cell = df_ne['cell_load'].std()
    cell_anomalies = df_ne[df_ne['cell_load'] > mean_cell + 2 * std_cell]
    if len(cell_anomalies) > 0:
        anomalies.append(f"{ne}: аномально высокая загрузка ячеек (среднее {mean_cell:.2f}%, пик {df_ne['cell_load'].max():.2f}%)")
    
    # Latency аномалии
    mean_lat = df_ne['latency_ms'].mean()
    std_lat = df_ne['latency_ms'].std()
    lat_anomalies = df_ne[df_ne['latency_ms'] > mean_lat + 2 * std_lat]
    if len(lat_anomalies) > 0:
        anomalies.append(f"{ne}: аномально высокая задержка (среднее {mean_lat:.2f} мс, stddev {std_lat:.2f} мс), пик {df_ne['latency_ms'].max():.2f} мс")
    
    # RRC conn отклонения
    mean_rrc = df_ne['rrc_conn'].mean()
    std_rrc = df_ne['rrc_conn'].std()
    rrc_anomalies = df_ne[(df_ne['rrc_conn'] < mean_rrc - 2 * std_rrc) | (df_ne['rrc_conn'] > mean_rrc + 2 * std_rrc)]
    if len(rrc_anomalies) > 0:
        anomalies.append(f"{ne}: аномальное количество RRC соединений (среднее {mean_rrc:.0f}, stddev {std_rrc:.0f}, пик {df_ne['rrc_conn'].max():.0f})")
    
    # PRB utilization аномалии
    mean_prb = df_ne['prb_util'].mean()
    std_prb = df_ne['prb_util'].std()
    prb_anomalies = df_ne[df_ne['prb_util'] > mean_prb + 2 * std_prb]
    if len(prb_anomalies) > 0:
        anomalies.append(f"{ne}: аномально высокая загрузка ресурсов (среднее {mean_prb:.2f}%, stddev {std_prb:.2f}%), пик {df_ne['prb_util'].max():.2f}%")

# Запись аномалий
anomalies_file = output_dir / 'results' / 'anomalies.tsv'
with open(anomalies_file, 'w') as f:
    f.write("Аномалии:\n")
    for anomaly in anomalies:
        f.write(f"- {anomaly}\n")

# Генерация графиков
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Строим временные ряды для каждой БС
fig, axes = plt.subplots(5, 3, figsize=(18, 24))
fig.suptitle('Анализ данных по БС с низким трафиком (14 дней)', fontsize=16)

for i, ne in enumerate(sorted_bss):
    df_ne = df[df['ne'] == ne].sort_values('dt')
    
    # Общий трафик
    axes[i, 0].plot(df_ne['dt'], df_ne['total_traffic'], marker='o')
    axes[i, 0].set_title(f'{ne}: Общий трафик')
    axes[i, 0].set_ylabel('Трафик (MB)')
    axes[i, 0].tick_params(axis='x', rotation=45)
    
    # Drop rate
    axes[i, 1].plot(df_ne['dt'], df_ne['drop_rate'], marker='o', color='red')
    axes[i, 1].set_title(f'{ne}: Drop rate')
    axes[i, 1].set_ylabel('%')
    axes[i, 1].tick_params(axis='x', rotation=45)
    
    # Cell load
    axes[i, 2].plot(df_ne['dt'], df_ne['cell_load'], marker='o', color='orange')
    axes[i, 2].set_title(f'{ne}: Загрузка ячеек')
    axes[i, 2].set_ylabel('%')
    axes[i, 2].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig(output_dir / 'plots' / 'traffic_analysis.png', dpi=150)

# Вывод результатов
print("=== Резюме по БС с низким трафиком (14 дней) ===")
print("\nРанжирование по среднему трафику:")
for i, ne in enumerate(sorted_bss):
    print(f"{i+1}. {ne}: {results[ne]['mean_total_traffic']:.2f} MB (медиана: {results[ne]['median_total_traffic']:.2f} MB)")

print("\n=== Аномалии ===")
for anomaly in anomalies:
    print(anomaly)

print(f"\nОтчет сохранен в {results_file}")
print(f"Графики сохранены в {output_dir / 'plots' / 'traffic_analysis.png'}")
