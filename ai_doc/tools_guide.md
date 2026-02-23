# Тулы агента: просмотр и добавление

Краткое руководство по тому, где живут инструменты (tools) агента, как их просматривать и как добавлять новые.

---

## Где смотреть текущие тулы

### 1. Реестр в коде

Все тулы, доступные агенту, объявлены в **`agent.py`** в функции `create_agent()` — список `tools` (примерно строки 269–282):

```python
tools = [
    search_md_docs,
    search_md_docs_semantic,
    query_stats_db,
    save_agent_file,
    load_agent_file,
    list_agent_storage,
    list_agent_temp,
    clean_agent_temp,
    execute_analysis_script,
    list_experiment_artifacts,
    run_subagent,
    get_background_task_result,
]
```

Имена в списке — это функции, помеченные декоратором `@tool` в том же файле (или импортированные). По ним видно полный набор инструментов.

### 2. Описания для модели

Для каждой функции с `@tool` описание берётся из **docstring**. Его видит LLM при выборе инструмента. Пример:

```python
@tool
def search_md_docs(query: str, max_results: int = 10) -> str:
    """Полнотекстовый поиск по локальным Markdown-документам (MD_DOCUMENTS_PATH)."""
    ...
```

Просмотр текущих тулов = просмотр этого списка в `create_agent()` и соответствующих `@tool`-функций с их docstring’ами в `agent.py`.

### 3. Логи вызовов

При работе агента каждый вызов тула логируется в консоль через обёртку `_wrap_tool_logging` (префикс `[tool]`). По логам видно, какие тулы реально вызываются.

---

## Текущий набор тулов (кратко)

| Тула | Назначение |
|------|------------|
| `search_md_docs` | Полнотекстовый поиск по MD (MD_DOCUMENTS_PATH) |
| `search_md_docs_semantic` | Семантический поиск по MD (индекс в ai_data) |
| `query_stats_db` | Read-only SQL к ai_data/network_stats.db |
| `save_agent_file` | Сохранить файл в AGENT_STORAGE_PATH / AGENT_TEMP_PATH |
| `load_agent_file` | Загрузить файл из хранилища агента |
| `list_agent_storage` | Список файлов в постоянном хранилище |
| `list_agent_temp` | Список файлов во временной папке |
| `clean_agent_temp` | Очистить временную папку агента |
| `execute_analysis_script` | Запуск аналитического скрипта (ai_experiments) |
| `list_experiment_artifacts` | Список артефактов сценария в ai_experiments |
| `run_subagent` | Запуск субагента (синхронно или в фоне) |
| `get_background_task_result` | Результат фоновой задачи по task_id |

Реализация части тулов вынесена в модули каталога **`tools/`** (например `tools/agent_storage.py`, `tools/analysis_runner.py`, `tools/md_search.py`, `tools/stats_db.py`).

---

## Как добавить новый тул

### Шаг 1: Решить, где писать логику

- **Простая логика, только для агента** — можно реализовать прямо в `agent.py` в функции с `@tool`.
- **Сложная или переиспользуемая логика** — вынести в модуль в **`tools/`**, в `agent.py` оставить только обёртку с `@tool`, вызывающую эту логику.

### Шаг 2: Описать функцию и пометить `@tool`

Используется декоратор **`@tool`** из `langchain_core.tools` (уже импортирован в `agent.py`).

- **Docstring** — краткое описание для модели: что делает тул, какие аргументы что означают. От этого зависит, когда модель будет вызывать инструмент.
- **Типы аргументов** — по возможности указывать (str, int, bool и т.д.), чтобы схема для LLM генерировалась корректно.
- **Возврат** — обычно `str` (агент получает текст результата).

Пример минимального тула в `agent.py`:

```python
@tool
def my_new_tool(query: str, limit: int = 10) -> str:
    """Краткое описание: что делает тул и когда его использовать."""
    # вызов своей логики или код здесь
    result = do_something(query, limit)
    return str(result)
```

Если логика в `tools/`:

```python
# в agent.py
from tools.my_module import do_something

@tool
def my_new_tool(query: str, limit: int = 10) -> str:
    """Краткое описание: что делает тул и когда его использовать."""
    return str(do_something(query, limit))
```

### Шаг 3: Зарегистрировать тул в агенте

В `create_agent()` добавить новую функцию в список `tools`:

```python
tools = [
    search_md_docs,
    search_md_docs_semantic,
    # ...
    get_background_task_result,
    my_new_tool,   # добавить сюда
]
```

Обёртка `_wrap_tool_logging` применяется ко всем элементам списка, отдельно подключать её не нужно.

### Шаг 4: Специальные случаи

- **Тул с `ToolRuntime`** (как `run_subagent`): в сигнатуру добавляется аргумент `runtime: ToolRuntime`; его не описывать в docstring как пользовательский параметр — его передаёт фреймворк.
- **Тулы, требующие окружения**: использовать переменные из `os.environ` или `PROJECT_ROOT` (как в `search_md_docs`).

---

## Итог

- **Просмотр тулов:** список в `create_agent()` в `agent.py` + соответствующие `@tool`-функции и их docstring; при необходимости — реализация в `tools/`.
- **Добавление тула:** определить функцию с `@tool` и понятным docstring (и при необходимости вынести логику в `tools/`), затем добавить её в список `tools` в `create_agent()`.

Отличие от skills: тул — атомарное действие («руки» агента); skill — процесс, стратегия, инструкция. Подробнее — в `ai_doc/agent_architecture_insights.md`.
