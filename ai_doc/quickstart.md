# Quickstart

```bash
python tools/fake_network_stats.py --db ai_data/network_stats.db create-schema
python tools/fake_network_stats.py --db ai_data/network_stats.db generate --days 365 --sites 100 --groups 5 --seed 42 --if-exists replace
```

Агент может отвечать на вопросы по статистике из `ai_data/network_stats.db` через тул запросов к БД.
