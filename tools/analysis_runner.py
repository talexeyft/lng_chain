#!/usr/bin/env python3
"""
Запуск сгенерированных аналитических скриптов с таймаутом и сохранением логов.
Артефакты сохраняются в ai_experiments/<scenario_id>/; запись только туда и в ai_data.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_EXPERIMENTS = PROJECT_ROOT / "ai_experiments"
AI_DATA = PROJECT_ROOT / "ai_data"
DB_PATH = AI_DATA / "network_stats.db"

# Разрешённые импорты в сгенерированном коде (для проверки перед запуском)
ALLOWED_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from\s+(\w+)(?:\.\w+)*\s+import|import\s+(\w+)(?:\.\w+)*)"
)
FORBIDDEN = {"subprocess", "os.system", "eval", "exec", "__import__"}  # базовая фильтрация; open разрешён для записи в OUTPUT_DIR


def _check_script_imports(script_content: str) -> str | None:
    """Проверяет, что в скрипте нет явно запрещённых конструкций. Возвращает None или сообщение об ошибке."""
    lines = script_content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for bad in FORBIDDEN:
            if bad in stripped and not stripped.startswith("#"):
                return f"Запрещённая конструкция в скрипте: {bad}"
    return None


def run_analysis_script(
    scenario_id: str,
    script_content: str,
    timeout_sec: int = 120,
) -> dict:
    """
    Сохраняет script_content в ai_experiments/<scenario_id>/analysis.py,
    запускает его с таймаутом, пишет лог в run.log.
    Возвращает dict: success, message, log_path, result_paths, error.
    """
    err = _check_script_imports(script_content)
    if err:
        return {"success": False, "message": err, "log_path": None, "result_paths": [], "error": err}

    scenario_id = scenario_id.strip().replace(" ", "_")
    if not scenario_id or ".." in scenario_id or "/" in scenario_id:
        return {
            "success": False,
            "message": "Недопустимый scenario_id.",
            "log_path": None,
            "result_paths": [],
            "error": "Invalid scenario_id",
        }

    scenario_dir = AI_EXPERIMENTS / scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "results").mkdir(exist_ok=True)
    (scenario_dir / "plots").mkdir(exist_ok=True)

    script_path = scenario_dir / "analysis.py"
    script_path.write_text(script_content, encoding="utf-8")
    log_path = scenario_dir / "run.log"

    env = os.environ.copy()
    env["OUTPUT_DIR"] = str(scenario_dir)
    env["DB_PATH"] = str(DB_PATH) if DB_PATH.exists() else ""
    env["PYTHONUNBUFFERED"] = "1"

    try:
        with open(log_path, "w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(scenario_dir),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[Превышен таймаут {timeout_sec} с]\n")
                return {
                    "success": False,
                    "message": f"Таймаут {timeout_sec} с.",
                    "log_path": f"ai_experiments/{scenario_id}/run.log",
                    "result_paths": [],
                    "error": "Timeout",
                }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "log_path": f"ai_experiments/{scenario_id}/run.log",
            "result_paths": [],
            "error": str(e),
        }

    result_paths = []
    for sub in ("results", "plots"):
        d = scenario_dir / sub
        if d.exists():
            for f in d.iterdir():
                if f.is_file():
                    result_paths.append(f"ai_experiments/{scenario_id}/{sub}/{f.name}")

    if proc.returncode != 0:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        return {
            "success": False,
            "message": f"Скрипт завершился с кодом {proc.returncode}.",
            "log_path": f"ai_experiments/{scenario_id}/run.log",
            "result_paths": result_paths,
            "error": log_text[-2000:] if len(log_text) > 2000 else log_text,
        }

    return {
        "success": True,
        "message": "Выполнено успешно.",
        "log_path": f"ai_experiments/{scenario_id}/run.log",
        "result_paths": result_paths,
        "error": None,
    }


def list_experiment_artifacts(scenario_id: str) -> dict:
    """Возвращает список файлов в папке сценария: analysis.py, run.log, results/*, plots/*."""
    scenario_id = scenario_id.strip().replace(" ", "_")
    if not scenario_id or ".." in scenario_id or "/" in scenario_id:
        return {"scenario_id": scenario_id, "exists": False, "files": []}
    scenario_dir = AI_EXPERIMENTS / scenario_id
    if not scenario_dir.is_dir():
        return {"scenario_id": scenario_id, "exists": False, "files": []}
    files = []
    for p in scenario_dir.rglob("*"):
        if p.is_file():
            files.append(p.relative_to(PROJECT_ROOT).as_posix())
    return {"scenario_id": scenario_id, "exists": True, "files": sorted(files)}
