# Quickstart

## 1) Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Настройка переменных окружения

```bash
cp .env.example .env
```

Заполните в `.env`:
- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
- `DEEP_AGENT_MODEL` (опционально)

## 3) Запуск агента

```bash
python agent.py
```

Один запрос без интерактива (таймаут по умолчанию 300 с, лимит шагов 80):

```bash
python agent.py --query "какие бс имеют наиболее низкий траффик голоса"
```

При зависании: проверьте, что Ollama запущен и модель отвечает. Можно увеличить таймаут: `AGENT_INVOKE_TIMEOUT=600 python agent.py --query "..."`.

## 4) Пример запуска генератора презентации вручную

```bash
python skills/presentation/create_presentation.py --input ai_data/slides.json --output ai_data/demo.pptx
```

## 5) Конвертация PDF в Markdown

```bash
python tools/pdf2md.py путь/к/документ.pdf
python tools/pdf2md.py документ.pdf -o ai_doc/документ.md
python tools/pdf2md.py документ.pdf --images --pages 1,3,5-10
```

## 6) Пакетная конвертация документов (SRC_DOCUMENTS_PATH → MD_DOCUMENTS_PATH)

В `.env` задайте `SRC_DOCUMENTS_PATH` и `MD_DOCUMENTS_PATH`.

```bash
python tools/convert_docs.py
python tools/convert_docs.py --dry-run
python tools/convert_docs.py --src /path/to/pdf --dst /path/to/md --images
```

## 7) Индексация Markdown-документов

```bash
python tools/md_index.py
python tools/md_index.py --root /path/to/md --output ai_data/md_manifest.json
```

## 8) Поиск по Markdown-документам

Полнотекстовый поиск:

```bash
python tools/md_search.py fulltext "handover procedure"
python tools/md_search.py fulltext "RAN feature" --max-results 30
```

Семантический индекс и поиск (локальная Ollama-модель `qwen3-embedding:4b`):

```bash
python tools/md_search.py semantic-index
python tools/md_search.py semantic-search "как выполняется handover в nsa?"
```

## 9) Статистика сети (SQLite)

База: `ai_data/network_stats.db`, таблица **`hour_stats`** — почасовая статистика 3G по сотам. Запросы к ней выполняет агент через инструмент `query_stats_db` (только SELECT). Навык: `skills/technical-stats/`. Колонки: `dt`, `cellname`, `cs_traffic`, `ps_traffic`, KPI качества (`voice_dcr`, `rrc_dcr`, `cell_availability`, `cssr_amr` и др.).

Загрузка почасовой статистики из xlsx: `python tools/load_hour_stats.py --db ai_data/network_stats.db --xlsx "srcdata/..." --if-exists replace`.

Создание схемы и генерация тестовых данных для таблицы `network_stats` (опционально):

```bash
python tools/fake_network_stats.py create-schema --db ai_data/network_stats.db
python tools/fake_network_stats.py generate --db ai_data/network_stats.db --days 365 --sites 100
```

## 10) Аналитика «низкий трафик БС» (с план/отчёт и скриптами)

Агент строит план, выполняет SQL и при необходимости генерирует и запускает аналитические скрипты (pandas/графики), затем формирует FINAL_REPORT. Артефакты: `ai_experiments/<scenario_id>/`.

Пример запроса (один прогон без интерактива):

```bash
python agent.py --query "Найди БС с самым низким трафиком за последние 14 дней, проведи анализ причин и сформируй краткий отчёт с выводами и путями к графикам."
```

Параметры сценария (период, топ-N, порог просадки) задаются в запросе или по умолчанию из навыка technical-stats.
