import pandas as pd
from scipy import stats

df = pd.read_csv('/home/alex/code/lng_chain/ai_data/query_e7db0e7c.tsv', sep='\t')

corr_cs_ps, _ = stats.pearsonr(df['cs_traffic_sum'], df['ps_traffic_sum'])
corr_cs_au, _ = stats.pearsonr(df['cs_traffic_sum'], df['active_user_avg'])

print(f"Корреляция Пирсона (cs_traffic_sum, ps_traffic_sum): {corr_cs_ps:.4f}")
print(f"Корреляция Пирсона (cs_traffic_sum, active_user_avg): {corr_cs_au:.4f}")
