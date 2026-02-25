import json
import os
import sys
import time
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool, tool
from langgraph.checkpoint.memory import MemorySaver
from tools.agent_storage import (
    clean_temp,
    list_files as list_storage_files,
    load_file as load_agent_file_content,
    save_file as save_agent_file_content,
)
# execute_analysis_script отключён: агент не пишет и не запускает Python-скрипты
# from tools.analysis_runner import list_experiment_artifacts as list_experiment_artifacts_impl
# from tools.analysis_runner import run_analysis_script
from tools.md_search import search_fulltext, search_semantic
from tools.stats_db import run_stats_query

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent

# Инструменты веб-поиска и парсинга отключены (fetch_url, TavilySearchResults).
# Скиллы deep-research и web-search перенесены в archive_skills.


@tool
def search_md_docs(query: str, max_results: int = 10) -> str:
    """Полнотекстовый поиск по локальным Markdown-документам (MD_DOCUMENTS_PATH)."""
    root = Path(os.environ.get("MD_DOCUMENTS_PATH", "")).expanduser().resolve()
    if not root.exists():
        return f"Папка MD_DOCUMENTS_PATH не найдена: {root}"

    manifest_path = PROJECT_ROOT / "ai_data" / "md_manifest.json"
    manifest = manifest_path if manifest_path.exists() else None
    results = search_fulltext(
        query=query,
        root=root,
        manifest_path=manifest,
        max_results=max_results,
    )
    if not results:
        return "Ничего не найдено."

    lines = [f"Найдено: {len(results)}"]
    for item in results:
        lines.append(f"- {item['path']}:{item['line']} — {item['snippet']}")
    return "\n".join(lines)


@tool
def search_md_docs_semantic(query: str, max_results: int = 10) -> str:
    """Семантический поиск по локальным Markdown-документам (индекс ai_data/md_semantic_index.jsonl)."""
    index_path = PROJECT_ROOT / "ai_data" / "md_semantic_index.jsonl"
    if not index_path.exists():
        return (
            "Семантический индекс не найден. "
            "Постройте его: python tools/md_search.py semantic-index"
        )

    try:
        results = search_semantic(
            query=query,
            semantic_index_path=index_path,
            model_name=os.environ.get("MD_EMBEDDING_MODEL", "qwen3-embedding:4b"),
            max_results=max_results,
        )
    except RuntimeError as exc:
        return str(exc)
    if not results:
        return "Ничего не найдено."

    lines = [f"Найдено: {len(results)}"]
    for item in results:
        lines.append(
            f"- score={item['score']:.4f} | {item['path']}#{item['chunk_id']} — {item['snippet']}"
        )
    return "\n".join(lines)


@tool
def query_stats_db(sql: str, max_rows: int = 500, save_to_file: bool = False) -> str:
    """Выполняет read-only SQL (только SELECT) к локальной базе статистики ai_data/network_stats.db.
    Таблица: hour_stats (dt, cellname, cs_traffic, ps_traffic, cell_availability, cssr_amr, voice_dcr,
    rrc_cssr, rrc_dcr, packet_ssr, hsdpa_sr, rab_ps_dcr_user, hsdpa_end_usr_thrp, sho_factor, sho_sr,
    rtwp, cs_att, ps_att, branch, active_user, code_block).
    save_to_file=True: результат сохраняется в ai_data/query_<id>.tsv, в ответе — путь и сводка (строки, колонки), без полного дампа в контекст."""
    return run_stats_query(sql=sql, max_rows=max_rows, save_to_file=save_to_file)


@tool
def save_agent_file(relative_path: str, content: str, temp: bool = False) -> str:
    """Сохраняет файл в выделенную папку агента (AGENT_STORAGE_PATH или AGENT_TEMP_PATH).
    relative_path — путь внутри папки, например reports/summary.md. temp=True — во временную папку."""
    return save_agent_file_content(relative_path, content, temp=temp)


@tool
def load_agent_file(relative_path: str, from_temp: bool = False) -> str:
    """Загружает содержимое файла из папки агента (постоянной или временной)."""
    return load_agent_file_content(relative_path, from_temp=from_temp)


@tool
def list_agent_storage() -> str:
    """Список файлов в постоянном хранилище агента (AGENT_STORAGE_PATH)."""
    return list_storage_files(temp=False)


@tool
def list_agent_temp() -> str:
    """Список файлов во временной папке агента (AGENT_TEMP_PATH)."""
    return list_storage_files(temp=True)


@tool
def clean_agent_temp() -> str:
    """Удаляет все файлы во временной папке агента. Использовать для периодической очистки."""
    return clean_temp()


# execute_analysis_script и list_experiment_artifacts отключены — агент не пишет и не запускает Python-скрипты


def _run_subagent_impl(description: str, background: bool, runtime: ToolRuntime) -> str:
    """Внутренняя реализация run_subagent: проверка глубины, запуск синхронно или в фоне."""
    configurable = runtime.config.get("configurable") or {}
    depth = configurable.get("subagent_depth", 0)
    if depth >= MAX_SUBAGENT_DEPTH:
        return f"Достигнут лимит вложенности ({MAX_SUBAGENT_DEPTH}). Нельзя запустить субагента."

    task_id = uuid.uuid4().hex
    thread_id = f"sub-{task_id}"
    sub_config = {
        "configurable": {"thread_id": thread_id, "subagent_depth": depth + 1},
        "recursion_limit": AGENT_RECURSION_LIMIT,
    }

    agent = create_agent()

    def _invoke() -> dict:
        return agent.invoke(
            {"messages": [HumanMessage(content=description)]},
            config=sub_config,
        )

    if not background:
        result = _invoke()
        messages = result.get("messages", [])
        if messages and hasattr(messages[-1], "content") and messages[-1].content:
            return str(messages[-1].content)
        return "Субагент завершился без текстового ответа."

    future = _subagent_executor.submit(_invoke)
    _background_tasks[task_id] = {"future": future, "thread_id": thread_id}
    return (
        f"Задача запущена в фоне. ID: {task_id}. "
        f"Результат: get_background_task_result(task_id=\"{task_id}\")."
    )


@tool
def run_subagent(
    description: str,
    background: bool,
    runtime: ToolRuntime,
) -> str:
    """Запускает субагента с тем же набором инструментов и skills для сложных или параллельных подзадач.
    description — формулировка задачи для субагента. background=False — дождаться результата и вернуть его;
    background=True — запустить в фоне и вернуть task_id; результат потом запросить через get_background_task_result(task_id).
    Результаты субагентов обрабатывай сам и формулируй ответ пользователю; не показывай пользователю внутренние task_id."""
    return _run_subagent_impl(description, background, runtime)


@tool
def get_background_task_result(task_id: str) -> str:
    """Возвращает результат фоновой задачи по task_id (выданному run_subagent с background=True).
    Если задача ещё выполняется — статус «ещё выполняется»; иначе — текст ответа субагента или сообщение об ошибке."""
    if task_id not in _background_tasks:
        return "Неизвестный task_id или сессия сброшена."
    entry = _background_tasks[task_id]
    future = entry["future"]
    if not future.done():
        return "Задача ещё выполняется."
    try:
        result = future.result(timeout=0)
        messages = result.get("messages", [])
        if messages and hasattr(messages[-1], "content") and messages[-1].content:
            return str(messages[-1].content)
        return "Субагент завершился без текстового ответа."
    except Exception as exc:
        return f"Ошибка субагента: {exc}"


def _wrap_tool_logging(original_tool):
    """Оборачивает инструмент: логирует вызовы в консоль. Возвращает новый инструмент."""
    orig_func = original_tool.func

    def logged_func(*args, **kwargs):
        inp = {
            k: v
            for k, v in kwargs.items()
            if k not in ("config", "run_manager", "callbacks")
        }
        if not inp and args:
            inp = args[0] if isinstance(args[0], dict) else {}
        args_preview = json.dumps(inp, ensure_ascii=False, default=str)
        if len(args_preview) > 200:
            args_preview = args_preview[:200] + "..."
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [tool] {original_tool.name}({args_preview})")
        result = orig_func(*args, **kwargs)
        ts_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        out_preview = str(result)[:80] + ("..." if len(str(result)) > 80 else "")
        print(f"[{ts_end}] [tool] {original_tool.name} -> {out_preview}")
        return result

    return StructuredTool(
        name=original_tool.name,
        description=original_tool.description,
        args_schema=original_tool.args_schema,
        func=logged_func,
    )


def create_agent():
    model_name = os.getenv("DEEP_AGENT_MODEL", "ollama:qwen3-coder-next")
    model = init_chat_model(model_name)

    tools = [
        search_md_docs,
        search_md_docs_semantic,
        query_stats_db,
        save_agent_file,
        load_agent_file,
        list_agent_storage,
        list_agent_temp,
        clean_agent_temp,
        # execute_analysis_script, list_experiment_artifacts — отключены
        run_subagent,
        get_background_task_result,
    ]
    tools = [_wrap_tool_logging(t) for t in tools]

    backend = FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=False)
    checkpointer = MemorySaver()

    skills_dir = PROJECT_ROOT / "skills"
    skill_sources = [
        str(skills_dir / name)
        for name in ("md-search", "presentation", "technical-stats")
        if (skills_dir / name).is_dir()
    ]

    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "Ты Deep Agent с поддержкой skills. "
            "Используй навыки из директории skills по принципу progressive disclosure. "
            "Для фактов из интернета всегда указывай источники. "
            "Делегирование подзадач делай через run_subagent (синхронно или в фоне); при фоне забирай результат через get_background_task_result. "
            "Пользователю отдавай только обработанный итог, без упоминания субагентов и task_id, если это не требуется по запросу.\n\n"
            "Аналитический контракт (запросы на аналитику KPI, трафика, отчёты по БС):\n"
            "1) Сначала сформируй PLAN: цель, гипотезы, шаги анализа, нужные данные, критерии завершения.\n"
            "2) Выполняй шаги по плану; после каждого — STEP_RESULT: что сделано, ключевые числа, подтверждена/отклонена гипотеза, confidence (0–1).\n"
            "3) Запрещено делать выводы без численного подтверждения (KPI, таблицы, графики).\n"
            "4) Анализ завершён только после FINAL_REPORT: проблемные БС, причины с подтверждающими KPI, пути к артефактам, рекомендации. Без FINAL_REPORT и сохранённых артефактов ответ не считать завершённым."
        ),
        backend=backend,
        skills=skill_sources,
        checkpointer=checkpointer,
    )


def run_cli() -> None:
    agent = create_agent()
    thread_id = f"thread-{uuid.uuid4()}"

    print("Deep Agent запущен. Введите запрос (exit для выхода):")
    while True:
        user_text = input("> ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            break

        config = {
            "configurable": {"thread_id": thread_id, "subagent_depth": 0},
            "recursion_limit": AGENT_RECURSION_LIMIT,
        }
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    agent.invoke,
                    {"messages": [{"role": "user", "content": user_text}]},
                    config=config,
                )
                result = future.result(timeout=AGENT_INVOKE_TIMEOUT)
        except FuturesTimeoutError:
            print(
                f"\nПревышено время ожидания ({AGENT_INVOKE_TIMEOUT} с). "
                "Проверьте Ollama; при необходимости увеличьте AGENT_INVOKE_TIMEOUT.",
                file=sys.stderr,
            )
            continue

        messages = result.get("messages", [])
        if messages:
            print(f"\n{messages[-1].content}\n")
        else:
            print("\nАгент не вернул ответа.\n")


# Таймаут одного вызова агента в режиме --query (секунды). Защита от зависания (Ollama/LLM не отвечает).
AGENT_INVOKE_TIMEOUT = int(os.environ.get("AGENT_INVOKE_TIMEOUT", "300"))
# Максимум шагов графа за один запрос (защита от зацикливания).
AGENT_RECURSION_LIMIT = int(os.environ.get("AGENT_RECURSION_LIMIT", "80"))
# Максимальная глубина вложенности субагентов (0=главный, 1–3=субагенты; на глубине 3 запуск вложенного запрещён).
MAX_SUBAGENT_DEPTH = 3
# Реестр фоновых задач: task_id -> {"future": Future, "thread_id": str}
_background_tasks: dict[str, dict] = {}
# Executor для фонового запуска субагентов
_subagent_executor = ThreadPoolExecutor(max_workers=4)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--query":
        query = sys.argv[2] if len(sys.argv) > 2 else "Найди в документации про handover."
        agent = create_agent()
        config = {
            "configurable": {"thread_id": "test-run", "subagent_depth": 0},
            "recursion_limit": AGENT_RECURSION_LIMIT,
        }
        print(f"Запрос: {query[:80]}{'...' if len(query) > 80 else ''}")
        print(f"Таймаут: {AGENT_INVOKE_TIMEOUT} с, лимит шагов: {AGENT_RECURSION_LIMIT}")
        print("(ожидание модели или вызов инструментов — при долгом ожидании будет выводиться «ждём…» каждые 15 с)", flush=True)
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    agent.invoke,
                    {"messages": [{"role": "user", "content": query}]},
                    config=config,
                )
                result = None
                deadline = time.monotonic() + AGENT_INVOKE_TIMEOUT
                while True:
                    left = max(1, int(deadline - time.monotonic()))
                    try:
                        result = future.result(timeout=min(15, left))
                        break
                    except FuturesTimeoutError:
                        if time.monotonic() >= deadline:
                            raise FuturesTimeoutError()
                        print("  ждём…", flush=True)
        except FuturesTimeoutError:
            print(
                f"\nПревышено время ожидания ({AGENT_INVOKE_TIMEOUT} с). "
                "Проверьте, что Ollama запущен и модель отвечает; при необходимости увеличьте AGENT_INVOKE_TIMEOUT.",
                file=sys.stderr,
            )
            sys.exit(124)
        for m in result.get("messages", []):
            if hasattr(m, "content") and m.content:
                print(m.content)
        sys.exit(0)
    run_cli()
