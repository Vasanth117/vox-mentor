"""
Safe code executor — runs Python, JavaScript, C, and C++ via subprocess
with timeout protection and temp file cleanup.
"""
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from config import CODE_TIMEOUT

TEMP_DIR = Path(tempfile.gettempdir()) / "voxmentor_exec"
TEMP_DIR.mkdir(exist_ok=True)


def _write_temp(code: str, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix, dir=TEMP_DIR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def _run(cmd: list[str], timeout: int = CODE_TIMEOUT) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TEMP_DIR),
        )
        return {
            "stdout": result.stdout[:4000],
            "stderr": result.stderr[:2000],
            "return_code": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "⏰ Execution timed out (5s limit).", "return_code": -1, "success": False}
    except FileNotFoundError as e:
        return {"stdout": "", "stderr": f"Runtime not found: {e}", "return_code": -1, "success": False}


def run_python(code: str) -> dict:
    path = _write_temp(code, ".py")
    try:
        return _run([sys.executable, path])
    finally:
        _safe_delete(path)


def run_javascript(code: str) -> dict:
    path = _write_temp(code, ".js")
    try:
        return _run(["node", path])
    finally:
        _safe_delete(path)


def run_c(code: str) -> dict:
    src = _write_temp(code, ".c")
    out = src.replace(".c", ".out")
    try:
        compile_res = _run(["gcc", src, "-o", out, "-lm"], timeout=15)
        if not compile_res["success"]:
            return compile_res
        return _run([out])
    finally:
        _safe_delete(src)
        _safe_delete(out)


def run_cpp(code: str) -> dict:
    src = _write_temp(code, ".cpp")
    out = src.replace(".cpp", ".out")
    try:
        compile_res = _run(["g++", src, "-o", out, "-std=c++17"], timeout=15)
        if not compile_res["success"]:
            return compile_res
        return _run([out])
    finally:
        _safe_delete(src)
        _safe_delete(out)


def _safe_delete(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


RUNNERS = {
    "python": run_python,
    "javascript": run_javascript,
    "js": run_javascript,
    "c": run_c,
    "cpp": run_cpp,
    "c++": run_cpp,
}


def execute_code(code: str, language: str) -> dict:
    lang = language.lower().strip()
    runner = RUNNERS.get(lang)
    if not runner:
        return {
            "stdout": "",
            "stderr": f"Language '{language}' is not supported. Supported: python, javascript, c, cpp",
            "return_code": -1,
            "success": False,
        }
    return runner(code)
