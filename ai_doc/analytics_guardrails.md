# Ограничения и структура хранения аналитики

## Guardrails

- **SQL**: только read-only (SELECT) через `query_stats_db` к `ai_data/network_stats.db` (таблица **hour_stats**). INSERT/UPDATE/DELETE запрещены.
- **Сгенерированные скрипты** (`execute_analysis_script`):
  - Разрешённые библиотеки: pandas, numpy, matplotlib, seaborn, sqlite3, pathlib, os, json.
  - Запрещённые конструкции: subprocess, os.system, eval, exec, __import__ (проверка в `tools/analysis_runner.py`).
  - Запись файлов только в каталог сценария (см. ниже); скрипт получает `OUTPUT_DIR` и `DB_PATH` через окружение.

## Структура хранения артефактов

| Назначение | Путь |
|------------|------|
| Промежуточные выгрузки, логи запросов, TSV | `ai_data/` |
| Прогоны сценариев аналитики | `ai_experiments/<scenario_id>/` |

Структура папки сценария:

- `ai_experiments/<scenario_id>/analysis.py` — сгенерированный скрипт
- `ai_experiments/<scenario_id>/run.log` — лог последнего запуска
- `ai_experiments/<scenario_id>/results/*.csv` — таблицы
- `ai_experiments/<scenario_id>/plots/*.png` — графики
- `ai_experiments/<scenario_id>/report.md` — итоговый отчёт (по желанию)

Скрипт должен использовать `os.environ.get("OUTPUT_DIR")` как корень для путей записи и сохранять данные в подпапках `results/` и `plots/`.
