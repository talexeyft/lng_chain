# Quickstart

```bash
python tools/fake_network_stats.py --db ai_data/network_stats.db create-schema
python tools/fake_network_stats.py --db ai_data/network_stats.db generate --days 365 --sites 100 --groups 5 --seed 42 --if-exists replace
```

Загрузка почасовой статистики 3G из xlsx в БД (таблица `hour_stats`):

```bash
python tools/load_hour_stats.py --db ai_data/network_stats.db --xlsx "srcdata/3 пример часовая статистика 3G.xlsx" --if-exists replace
```

Агент может отвечать на вопросы по статистике из `ai_data/network_stats.db` (таблица `hour_stats`) через тул запросов к БД.
