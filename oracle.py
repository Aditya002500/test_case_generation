"""Subprocess-based oracle for ground-truth expected values.

Runs user-provided code in an isolated subprocess with strict timeouts and
resource limits. Supports Python today. The wrapper code is generated from
the spec's entry-point convention and a JSON payload that describes how to
call it.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Conservative defaults. These exist so a malicious or buggy submission cannot
# hang the host or fill the disk.
DEFAULT_TIMEOUT_S = 2.0
DEFAULT_MAX_OUTPUT_BYTES = 256 * 1024


@dataclass
class OracleResult:
    success: bool
    value: Any
    raw_stdout: str
    raw_stderr: str
    duration_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "value": self.value,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


def _build_python_wrapper(entry: str, code: str, call_style: str) -> str:
    """Construct the harness script.

    entry: function name to call, e.g. "two_sum" or "rev"
    call_style:
        - "args_list": payload is a JSON list, unpack as positional args
        - "kwargs": payload is a JSON object, pass as **kwargs
        - "stdin_single_arg": payload is a single value, the entry takes one arg
    """
    safe_code = textwrap.dedent(code).strip()
    prelude = (
        "import json, sys, traceback\n"
        "payload = sys.stdin.read()\n"
        "data = json.loads(payload)\n"
    )
    if call_style == "args_list":
        call = f"_args = data\n_args_list = _args if isinstance(_args, list) else [_args]\nresult = {entry}(*_args_list)\n"
    elif call_style == "kwargs":
        call = f"result = {entry}(**data)\n"
    else:  # stdin_single_arg
        call = f"result = {entry}(data)\n"
    return (
        prelude
        + safe_code
        + "\n\n"
        + call
        + "sys.stdout.write('###STDOUT###' + json.dumps(result, default=str) + '###END###')\n"
    )


def _set_limits() -> None:
    """Apply POSIX resource limits inside the child process."""
    if platform.system() == "Windows":
        return
    try:
        # 256 MB virtual memory cap
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        # 5 seconds of CPU
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    except (ValueError, OSError):
        pass


def _resolve_python() -> str:
    """Find a Python interpreter that is not the current one if possible."""
    return shutil.which("python3") or shutil.which("python") or sys.executable


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def _apply_child_limits() -> None:
    """Apply POSIX resource limits inside the child process."""
    if platform.system() == "Windows":
        return
    try:
        # 256 MB virtual memory cap
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        # 5 seconds of CPU
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    except (ValueError, OSError):
        pass


def run_python_oracle(
    code: str,
    entry: str,
    payload: Any,
    *,
    call_style: str = "args_list",
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> OracleResult:
    """Run a Python function with `payload` as input and capture the return value as JSON.

    The function must be JSON-serialisable on both ends; values that cannot be
    serialised fall back to ``str(value)`` which can be inspected by callers.
    """
    wrapper = _build_python_wrapper(entry, code, call_style)
    payload_text = json.dumps(payload, default=str)
    interpreter = _resolve_python()

    with tempfile.TemporaryDirectory(prefix="spectest_oracle_") as tmp:
        script_path = os.path.join(tmp, "harness.py")
        with open(script_path, "w") as fp:
            fp.write(wrapper)

        # Use a fresh process group so we can kill the whole tree on timeout.
        preexec = _apply_child_limits if platform.system() != "Windows" else None
        if platform.system() != "Windows":

            def _preexec() -> None:
                os.setsid()
                _apply_child_limits()

            preexec = _preexec

        start = _now_ms()
        try:
            proc = subprocess.run(
                [interpreter, "-I", script_path],
                input=payload_text,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
                preexec_fn=preexec,
            )
        except subprocess.TimeoutExpired as exc:
            return OracleResult(
                False,
                None,
                exc.stdout or "",
                exc.stderr or "",
                _now_ms() - start,
                error=f"timeout after {timeout_s}s",
            )
        except FileNotFoundError as exc:
            return OracleResult(False, None, "", "", _now_ms() - start, error=str(exc))

        duration = _now_ms() - start
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""

        if proc.returncode != 0:
            return OracleResult(
                False,
                None,
                stdout,
                stderr,
                duration,
                error=f"exit code {proc.returncode}: {stderr.strip()[:500]}",
            )

        marker_start = stdout.find("###STDOUT###")
        marker_end = stdout.rfind("###END###")
        if marker_start == -1 or marker_end == -1 or marker_end <= marker_start:
            return OracleResult(
                False,
                None,
                stdout,
                stderr,
                duration,
                error="oracle did not emit a parseable result marker",
            )

        raw = stdout[marker_start + len("###STDOUT###") : marker_end]
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            return OracleResult(
                False,
                raw,
                stdout,
                stderr,
                duration,
                error=f"oracle returned non-JSON: {exc}",
            )
        return OracleResult(True, value, stdout, stderr, duration)
