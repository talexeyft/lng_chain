import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from pathlib import Path

# Настройки
INPUT_FILE = '/home/alex/code/lng_chain/ai_data/query_443f2f9c.tsv'
OUTPUT_DIR = Path('results')
PLOTS_DIR = Path('plots')
SUMMARY_FILE = 'results/summary.tsv'

# Создание выходных директорий
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Лог-файл
log_lines = []

def log(msg):
    log_lines.append(msg)
    print(msg)

# 1. Загрузка данных
log("Загрузка данных из TSV файла...")
df = pd.read_csv(INPUT_FILE, sep='\t')
log(f"Загружено {len(df)} строк и {len(df.columns)} колонок")
log(f"Колонки: {list(df.columns)}")

# 2. EDA: Среднее значение pct_edrx
pct_edrx_mean = df['pct_edrx'].mean()
log(f"Среднее значение pct_edrx: {pct_edrx_mean:.4f}")

# Найти дни/временные окна, где pct_edrx упало более чем на 30% от среднего
threshold_30pct = pct_edrx_mean * 0.7  # 30% от среднего = 70% от порога
log(f"Порог для падения более чем на 30% от среднего: {threshold_30pct:.4f}")

# Анализ по сравнению со средним
df['drop_from_mean'] = df['pct_edrx'] < threshold_30pct
drop_from_mean_count = df['drop_from_mean'].sum()
log(f"Количество записей, где pct_edrx упало более чем на 30% от среднего: {drop_from_mean_count}")

# Анализ по сравнению с предыдущим значением (падение более чем на 30% от предыдущего)
df['pct_edrx_shift'] = df['pct_edrx'].shift(1)
df['pct_edrx_diff'] = df['pct_edrx'] - df['pct_edrx_shift']
# Падение более чем на 30% от предыдущего значения: текущее < 70% от предыдущего
df['drop_from_previous'] = df['pct_edrx'] < (df['pct_edrx_shift'] * 0.7)
drop_from_previous_count = df['drop_from_previous'].sum()
log(f"Количество записей, где pct_edrx упало более чем на 30% от предыдущего значения: {drop_from_previous_count}")

# 3. Корреляции
metrics = ['pct_edrx', 'traffic_ps', 'traffic_cs', 'calls', 'drop_rate', 'latency_ms', 'dl_mbps', 'ul_mbps', 'prb_util']
log("Расчет корреляций...")
correlation_matrix = df[metrics].corr()
log("Корреляционная матрица:")
log(correlation_matrix.to_string())

# Используем .corr() с указанными колонками
log("Корреляция pct_edrx с другими метриками:")
for col in metrics:
    if col != 'pct_edrx':
        corr = df['pct_edrx'].corr(df[col])
        log(f"pct_edrx vs {col}: {corr:.4f}")

# 4. Построение графиков
log("Построение графиков...")

# График 1: Динамика pct_edrx и traffic_ps
fig, ax1 = plt.subplots(figsize=(12, 6))

color1 = 'tab:red'
ax1.set_xlabel('Время')
ax1.set_ylabel('pct_edrx', color=color1)
ax1.plot(df.index, df['pct_edrx'], color=color1, marker='o', label='pct_edrx')
ax1.tick_params(axis='y', labelcolor=color1)

ax2 = ax1.twinx()
color2 = 'tab:blue'
ax2.set_ylabel('traffic_ps', color=color2)
ax2.plot(df.index, df['traffic_ps'], color=color2, marker='s', label='traffic_ps')
ax2.tick_params(axis='y', labelcolor=color2)

plt.title('Динамика pct_edrx и traffic_ps')
fig.tight_layout()

# Добавляем легенду
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

plt.savefig(PLOTS_DIR / 'edrx_traffic_trend.png', dpi=150, bbox_inches='tight')
plt.close()
log("График динамики сохранен: plots/edrx_traffic_trend.png")

# График 2: Корреляционная матрица
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, fmt='.3f')
plt.title('Корреляционная матрица eDRX и метрик сети')
plt.tight_layout()
plt.savefig(PLOTS_DIR / 'correlation_matrix.png', dpi=150, bbox_inches='tight')
plt.close()
log("Корреляционная матрица сохранена: plots/correlation_matrix.png")

# 5. Сохранение результатов
log("Сохранение результатов...")

# Фильтрация записей с падением eDRX (по любому из критериев)
drops_df = df[df['drop_from_mean'] | df['drop_from_previous']].copy()

# Очистка временных колонок
drops_df = drops_df.drop(columns=['drop_from_mean', 'drop_from_previous', 'pct_edrx_shift', 'pct_edrx_diff'])

# Сохранение summary.tsv
drops_df.to_csv(SUMMARY_FILE, sep='\t', index=False)
log(f"Summary файл сохранен: {SUMMARY_FILE}")

# Лог завершения
log("Анализ завершен успешно!")

# Возврат результатов
result_paths = [
    str(PLOTS_DIR / 'edrx_traffic_trend.png'),
    str(PLOTS_DIR / 'correlation_matrix.png'),
    str(SUMMARY_FILE)
]

# Создание run.log
with open('run.log', 'w') as f:
    f.write('\n'.join(log_lines))

print("\n=== ОТЧЕТ ===")
print(f"success: True")
print(f"log_path: run.log")
print(f"result_paths: {result_paths}")
print(f"error: None")
