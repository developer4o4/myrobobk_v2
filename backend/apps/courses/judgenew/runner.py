import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(getattr(settings, "JUDGE_RUNS_DIR", "/judge_runs"))
SANDBOX_IMAGE = getattr(settings, "JUDGE_IMAGE", "judge-sandbox:latest")
SECCOMP_PROFILE = Path(__file__).parent / "seccomp.json"

SUPPORTED_LANGUAGES = {"py", "c", "cpp"}


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int
    timeout: bool = False


def _truncate(text: str, limit: int = 8000) -> str:
    if not text:
        return ""
    if len(text) > limit:
        return text[:limit] + "\n... (chiqish qisqartirildi)"
    return text


def _docker_run(cmd: list[str], timeout_sec: int) -> RunResult:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        return RunResult(
            ok=(p.returncode == 0),
            stdout=_truncate(p.stdout),
            stderr=_truncate(p.stderr),
            exit_code=p.returncode,
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            ok=False,
            stdout=_truncate(e.stdout or ""),
            stderr="Vaqt limiti oshib ketdi (Time Limit Exceeded)",
            exit_code=124,
            timeout=True,
        )
    except Exception as e:
        logger.exception("Docker run error: %s", e)
        return RunResult(ok=False, stdout="", stderr=str(e), exit_code=1)


def _safe_write(path: Path, content: str) -> None:
    path.write_text(content or "", encoding="utf-8")
    os.chmod(path, 0o644)


def _prepare_job_dir(job_id: str) -> Path:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    td = BASE_DIR / job_id
    td.mkdir(mode=0o755, parents=True, exist_ok=False)
    return td


def _safe_cleanup(td: Path) -> None:
    if not td.exists():
        return
    try:
        real_base = BASE_DIR.resolve(strict=True)
        real_td = td.resolve(strict=True)
    except Exception:
        return
    if real_base not in real_td.parents:
        logger.error("Path traversal attempt detected: %s", td)
        return
    shutil.rmtree(real_td, ignore_errors=True)


def _build_base_cmd(td: Path) -> list[str]:
    # Container ichidagi /judge_runs -> serverda /tmp/judge_runs
    host_path = str(td).replace("/judge_runs", "/tmp/judge_runs")
    
    cmd = [
        "docker", "run", "--rm",
        "--memory", "256m",
        "--memory-swap", "256m",
        "--cpus", "0.5",
        "--pids-limit", "64",
        #"--cap-drop", "ALL",
        #"--security-opt", "no-new-privileges:true",
        "--user", "1000:1000",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
        "-v", f"{host_path}:/work:rw",  # ← host path ishlatiladi
        "-w", "/work",
    ]
    cmd.append(SANDBOX_IMAGE)
    cmd.append("sh")
    cmd.append("-c")
    return cmd

def run_in_sandbox(language: str, source_code: str, input_data: str) -> RunResult:
    if not shutil.which("docker"):
        return RunResult(False, "", "Docker CLI topilmadi", 1)

    if language not in SUPPORTED_LANGUAGES:
        return RunResult(False, "", f"Qo'llab-quvvatlanmaydigan til: {language}", 1)

    if not source_code or not source_code.strip():
        return RunResult(False, "", "Kod bo'sh", 1)

    job_id = str(uuid.uuid4())
    td = _prepare_job_dir(job_id)

    try:
        src_map = {"py": "main.py", "c": "main.c", "cpp": "main.cpp"}
        src_name = src_map[language]
        src_path = td / src_name
        input_path = td / "input.txt"

        _safe_write(src_path, source_code)
        _safe_write(input_path, input_data or "")

        base = _build_base_cmd(td)

        if language == "py":
            cmd = "timeout 5s python3 main.py < input.txt"
            return _docker_run(base + [cmd], timeout_sec=8)

        elif language == "c":
            compile_cmd = "timeout 15s gcc -O2 -std=c11 -Wall main.c -o app -lm"
            r = _docker_run(base + [compile_cmd], timeout_sec=18)
            if not r.ok:
                return r
            run_cmd = "timeout 5s ./app < input.txt"
            return _docker_run(base + [run_cmd], timeout_sec=8)

        else:  # cpp
            compile_cmd = "timeout 15s g++ -O2 -std=c++17 -Wall main.cpp -o app"
            r = _docker_run(base + [compile_cmd], timeout_sec=18)
            if not r.ok:
                return r
            run_cmd = "timeout 5s ./app < input.txt"
            return _docker_run(base + [run_cmd], timeout_sec=8)

    finally:
        _safe_cleanup(td)
