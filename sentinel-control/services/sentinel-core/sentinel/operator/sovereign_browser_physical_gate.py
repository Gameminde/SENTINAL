from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.browser_backend_contract import SENTINEL_CHROMIUM_BACKEND_ID
from sentinel.operator.real_browser_control_runtime import (
    BOUNDED_URL_AUTHORITY_REF,
    RealBrowserControlRuntimeError,
    RealBrowserEngine,
    build_sentinel_chromium_real_browser_engine_from_env,
)


@dataclass(frozen=True)
class BrowserProcessSnapshot:
    identity_hashes: tuple[str, ...]
    snapshot_error: str = ""

    @property
    def count(self) -> int:
        return len(self.identity_hashes)

    def delta_from(self, baseline: "BrowserProcessSnapshot") -> tuple[str, ...]:
        baseline_set = set(baseline.identity_hashes)
        return tuple(item for item in self.identity_hashes if item not in baseline_set)


EngineFactory = Callable[[Path, str, int], RealBrowserEngine]
ProcessSnapshotter = Callable[[], BrowserProcessSnapshot]


def run_sentinel_chromium_sovereign_physical_gate(
    *,
    capture_root: str | Path,
    target_url: str,
    cycles: int = 5,
    timeout_ms: int = 15_000,
    engine_factory: EngineFactory | None = None,
    process_snapshotter: ProcessSnapshotter | None = None,
    bundle_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run a bounded, safe physical proof for the canonical browser backend.

    The returned artifact intentionally contains only typed status, hashes and
    counts. It must not include raw URLs, local paths, DOM, profile material or
    process command lines.
    """

    root = Path(capture_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    factory = engine_factory or _default_engine_factory
    snapshotter = process_snapshotter or snapshot_browser_processes
    target_host = (urlparse(target_url).hostname or "").lower()
    target_origin_hash = _safe_origin_hash(target_url)
    started_at = time.monotonic()
    cycle_results: list[dict[str, Any]] = []

    for index in range(1, cycles + 1):
        cycle_root = root / f"cycle_{index:02d}"
        if cycle_root.exists():
            _remove_owned_tree(cycle_root, root)
        cycle_root.mkdir(parents=True, exist_ok=True)
        baseline = snapshotter()
        cycle = _run_single_cycle(
            cycle_index=index,
            cycle_root=cycle_root,
            target_url=target_url,
            target_host=target_host,
            target_origin_hash=target_origin_hash,
            timeout_ms=timeout_ms,
            engine_factory=factory,
            process_snapshotter=snapshotter,
            baseline=baseline,
        )
        cycle_results.append(cycle)

    passed_cycles = [item for item in cycle_results if item.get("cycle_passed") is True]
    close_completed_count = sum(1 for item in cycle_results if item.get("close_completed") is True)
    observation_count = sum(1 for item in cycle_results if item.get("observation_usable") is True)
    baseline_restore_count = sum(1 for item in cycle_results if item.get("process_baseline_restored") is True)
    profile_persisted = any(item.get("profile_material_persisted") is True for item in cycle_results)
    backend_ids = {str(item.get("actual_backend_id") or "") for item in cycle_results}
    cloak_dependency = any(item.get("cloak_dependency") is True for item in cycle_results)
    verdict = (
        "SOVEREIGN_PHYSICAL_GATE_PASSED"
        if len(passed_cycles) == cycles
        and backend_ids == {SENTINEL_CHROMIUM_BACKEND_ID}
        and close_completed_count == cycles
        and observation_count == cycles
        and baseline_restore_count == cycles
        and not profile_persisted
        and not cloak_dependency
        else "SOVEREIGN_PHYSICAL_GATE_FAILED"
    )
    result: dict[str, Any] = {
        "schema_version": "c5_sentinel_chromium_sovereign_physical_gate_v1",
        "verdict": verdict,
        "target_origin_hash": target_origin_hash,
        "target_host_hash": text_hash(target_host),
        "cycles_requested": cycles,
        "cycles_passed": len(passed_cycles),
        "provider_calls": 0,
        "product_browser_missions": 0,
        "external_network_scope": "bounded_public_read_only_browser_probe",
        "gates": {
            "launches": f"{sum(1 for item in cycle_results if item.get('launch_started') is True)}/{cycles}",
            "usable_context_page_observation": f"{observation_count}/{cycles}",
            "actual_backend_id": SENTINEL_CHROMIUM_BACKEND_ID if backend_ids == {SENTINEL_CHROMIUM_BACKEND_ID} else "MISMATCH",
            "cloak_dependency": cloak_dependency,
            "close_completed": f"{close_completed_count}/{cycles}",
            "owned_pid_tree_dead_before_next_cycle": f"{baseline_restore_count}/{cycles}",
            "process_baseline_restored": f"{baseline_restore_count}/{cycles}",
            "profile_material_persisted": profile_persisted,
            "terminal_receipt_unique": all(item.get("terminal_receipt_count") == 1 for item in cycle_results),
        },
        "cycles": cycle_results,
        "duration_ms": int((time.monotonic() - started_at) * 1000),
        "raw_dom_persisted": False,
        "raw_url_persisted": False,
        "raw_profile_path_persisted": False,
        "raw_process_command_line_persisted": False,
        "secrets_persisted": False,
    }
    if bundle_path is not None:
        _write_safe_bundle(Path(bundle_path), result)
    return result


def snapshot_browser_processes(*, root_pid: int | None = None) -> BrowserProcessSnapshot:
    if os.name != "nt":
        return BrowserProcessSnapshot(identity_hashes=(), snapshot_error="process_snapshot_unsupported_platform")
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object Name,ProcessId,ParentProcessId,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return BrowserProcessSnapshot(identity_hashes=(), snapshot_error=f"process_snapshot_failed:{type(exc).__name__}")
    if completed.returncode != 0:
        return BrowserProcessSnapshot(
            identity_hashes=(),
            snapshot_error=f"process_snapshot_command_failed:{completed.returncode}",
        )
    raw = completed.stdout.strip()
    if not raw:
        return BrowserProcessSnapshot(identity_hashes=())
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return BrowserProcessSnapshot(identity_hashes=(), snapshot_error="process_snapshot_json_invalid")
    rows = parsed if isinstance(parsed, list) else [parsed]
    root = int(root_pid if root_pid is not None else os.getpid())
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            parent = int(row.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            parent = 0
        by_parent.setdefault(parent, []).append(row)
    descendants: list[dict[str, Any]] = []
    stack = list(by_parent.get(root, ()))
    while stack:
        item = stack.pop()
        descendants.append(item)
        try:
            pid = int(item.get("ProcessId") or 0)
        except (TypeError, ValueError):
            pid = 0
        stack.extend(by_parent.get(pid, ()))
    hashes: list[str] = []
    for row in descendants:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "").lower()
        command_line = str(row.get("CommandLine") or "")
        command_lower = command_line.lower()
        if not (
            name in {"chrome.exe", "chromium.exe", "msedge.exe", "msedgewebview2.exe", "node.exe"}
            or "playwright" in command_lower
            or "chromium" in command_lower
            or "chrome" in command_lower
        ):
            continue
        hashes.append(
            stable_hash(
                {
                    "name": name,
                    "pid": int(row.get("ProcessId") or 0),
                    "ppid": int(row.get("ParentProcessId") or 0),
                    "command_hash": text_hash(command_line),
                }
            )
        )
    return BrowserProcessSnapshot(identity_hashes=tuple(sorted(set(hashes))))


def run_owned_stage_timeout_probe(
    *,
    stage: str,
    capture_root: str | Path,
    timeout_ms: int = 500,
) -> dict[str, Any]:
    root = Path(capture_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    started_at = time.monotonic()
    terminal_receipt_count = 0
    safe_stage = "".join(char for char in stage if char.isalnum() or char in {"_", "-"})[:64] or "unknown_stage"
    child_code = r"""
import json
import os
import subprocess
import sys
import time

stage = os.environ.get("SENTINEL_TIMEOUT_PROBE_STAGE", "unknown_stage")
grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
print(json.dumps({"event": "stage_started", "stage": stage, "pid": os.getpid(), "grandchild_pid": grandchild.pid}), flush=True)
time.sleep(30)
print(json.dumps({"event": "stage_returned", "stage": stage}), flush=True)
"""
    env = dict(os.environ)
    env["SENTINEL_TIMEOUT_PROBE_STAGE"] = safe_stage
    proc = subprocess.Popen(
        [sys.executable, "-c", child_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    stage_started = False
    stage_returned = False
    grandchild_pid = 0
    first_line = ""
    try:
        if proc.stdout is not None:
            first_line = proc.stdout.readline().strip()
        if first_line:
            parsed = json.loads(first_line)
            stage_started = parsed.get("event") == "stage_started"
            grandchild_pid = int(parsed.get("grandchild_pid") or 0)
    except Exception:
        stage_started = False
    timed_out = False
    try:
        proc.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
    if timed_out:
        _kill_process_tree(proc.pid)
    stdout_tail = ""
    stderr_tail = ""
    try:
        out, err = proc.communicate(timeout=2)
        stdout_tail = out or ""
        stderr_tail = err or ""
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            out, err = proc.communicate(timeout=2)
            stdout_tail = out or ""
            stderr_tail = err or ""
        except Exception:
            stdout_tail = ""
            stderr_tail = ""
    stage_returned = "stage_returned" in stdout_tail
    worker_alive = _process_exists(proc.pid)
    grandchild_alive = _process_exists(grandchild_pid) if grandchild_pid else False
    terminal_receipt_count += 1
    worker_terminated = not worker_alive
    process_tree_killed = worker_terminated and not grandchild_alive
    late_publication_blocked = not stage_returned
    result = {
        "schema_version": "c5_owned_stage_timeout_probe_v1",
        "stage": safe_stage,
        "stage_started": stage_started,
        "stage_returned": stage_returned,
        "timed_out": timed_out,
        "worker_pid_hash": stable_hash({"pid": proc.pid, "stage": safe_stage}),
        "grandchild_pid_hash": stable_hash({"pid": grandchild_pid, "stage": safe_stage}) if grandchild_pid else "",
        "worker_terminated": worker_terminated,
        "grandchild_terminated": not grandchild_alive,
        "process_tree_killed": process_tree_killed,
        "late_publication_blocked": late_publication_blocked,
        "terminal_receipt_count": terminal_receipt_count,
        "stderr_hash": text_hash(stderr_tail),
        "duration_ms": int((time.monotonic() - started_at) * 1000),
        "raw_path_persisted": False,
        "raw_command_line_persisted": False,
        "secrets_persisted": False,
    }
    return result


def summarize_sentinel_chromium_sovereign_boundary_probes(
    *,
    same_origin_allowed: bool,
    cross_origin_blocked: bool,
    cross_origin_cleanup_completed: bool,
    timeout_probes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    stage_results = {
        stage: _timeout_probe_passed(timeout_probes.get(stage, {}))
        for stage in ("launch", "context", "navigation")
    }
    return {
        "schema_version": "c5_sentinel_chromium_sovereign_boundary_summary_v1",
        "same_origin_allowed": bool(same_origin_allowed),
        "redirect_cross_origin_blocked": bool(cross_origin_blocked),
        "cross_origin_cleanup_completed": bool(cross_origin_cleanup_completed),
        "timeout_launch": stage_results["launch"],
        "timeout_context": stage_results["context"],
        "timeout_navigation": stage_results["navigation"],
        "physical_cancellation": all(stage_results.values()),
        "process_tree_kill": all(stage_results.values()),
        "late_publication_blocked": all(
            bool((timeout_probes.get(stage) or {}).get("late_publication_blocked"))
            for stage in ("launch", "context", "navigation")
        ),
        "terminal_receipt_unique": all(
            int((timeout_probes.get(stage) or {}).get("terminal_receipt_count") or 0) == 1
            for stage in ("launch", "context", "navigation")
        ),
        "boundary_gate_passed": bool(
            same_origin_allowed
            and cross_origin_blocked
            and cross_origin_cleanup_completed
            and all(stage_results.values())
        ),
    }


def _timeout_probe_passed(probe: dict[str, Any]) -> bool:
    return bool(
        probe.get("worker_terminated") is True
        and probe.get("process_tree_killed") is True
        and probe.get("late_publication_blocked") is True
        and int(probe.get("terminal_receipt_count") or 0) == 1
    )


def _run_single_cycle(
    *,
    cycle_index: int,
    cycle_root: Path,
    target_url: str,
    target_host: str,
    target_origin_hash: str,
    timeout_ms: int,
    engine_factory: EngineFactory,
    process_snapshotter: ProcessSnapshotter,
    baseline: BrowserProcessSnapshot,
) -> dict[str, Any]:
    started_at = time.monotonic()
    terminal_receipt_count = 0
    close_called = False
    close_completed = False
    failure_code = ""
    exception_class_hash = ""
    open_started = False
    open_completed = False
    observation_usable = False
    actual_backend_id = "unknown"
    session_backend_kind = "unknown"
    snapshot_hash = ""
    engine: RealBrowserEngine | None = None
    try:
        engine = engine_factory(cycle_root, target_url, timeout_ms)
        actual_backend_id = str(getattr(engine, "browser_backend_id", "unknown") or "unknown")
        session_backend_kind = str(getattr(engine, "session_manager_backend_kind", "unknown") or "unknown")
        bind_authority = getattr(engine, "bind_authority", None)
        if callable(bind_authority):
            bind_authority(_read_only_browser_authority(target_host=target_host))
        bind_root = getattr(engine, "bind_root_session_id", None)
        if callable(bind_root):
            bind_root(f"c5_sovereign_physical_cycle_{cycle_index}")
        open_started = True
        open_snapshot = engine.open()
        open_completed = True
        observe_snapshot = engine.observe()
        snapshot_hash = stable_hash(
            {
                "open_state_hash": getattr(open_snapshot, "state_hash", ""),
                "observe_state_hash": getattr(observe_snapshot, "state_hash", ""),
                "observe_title_hash": text_hash(str(getattr(observe_snapshot, "page_title", ""))),
                "element_count": len(tuple(getattr(observe_snapshot, "elements", ()) or ())),
            }
        )
        observation_usable = bool(getattr(observe_snapshot, "state_hash", "")) and bool(
            str(getattr(observe_snapshot, "page_title", "") or "").strip()
        )
    except Exception as exc:
        failure_code = _safe_failure_code("sovereign_browser_launch_or_observe_failed", exc)
        exception_class_hash = text_hash(exc.__class__.__name__)
    finally:
        if engine is not None:
            close_called = True
            try:
                close = getattr(engine, "close", None)
                if callable(close):
                    close()
                close_completed = True
            except Exception as exc:
                close_completed = False
                failure_code = "sovereign_browser_close_failed"
                exception_class_hash = text_hash(exc.__class__.__name__)
        terminal_receipt_count += 1

    after_close = _wait_for_baseline_restored(process_snapshotter=process_snapshotter, baseline=baseline)
    profile_material_count = _profile_material_count(cycle_root)
    survivor_delta = after_close.delta_from(baseline)
    process_baseline_restored = not survivor_delta and after_close.snapshot_error == ""
    profile_material_persisted = profile_material_count > 0
    if actual_backend_id != SENTINEL_CHROMIUM_BACKEND_ID and not failure_code:
        failure_code = "sovereign_browser_backend_mismatch"
    if profile_material_persisted and not failure_code:
        failure_code = "sovereign_browser_profile_material_persisted"
    if not process_baseline_restored and not failure_code:
        failure_code = "sovereign_browser_process_baseline_not_restored"
    cycle_passed = bool(
        open_started
        and open_completed
        and observation_usable
        and actual_backend_id == SENTINEL_CHROMIUM_BACKEND_ID
        and close_completed
        and process_baseline_restored
        and not profile_material_persisted
        and terminal_receipt_count == 1
    )
    return {
        "cycle": cycle_index,
        "cycle_root_hash": stable_hash(str(cycle_root)),
        "launch_started": open_started,
        "launch_completed": open_completed,
        "context_page_usable": observation_usable,
        "observation_usable": observation_usable,
        "actual_backend_id": actual_backend_id,
        "session_backend_kind": session_backend_kind,
        "cloak_dependency": False,
        "close_called": close_called,
        "close_completed": close_completed,
        "process_baseline_count": baseline.count,
        "process_after_close_count": after_close.count,
        "process_baseline_restored": process_baseline_restored,
        "owned_process_survivor_count": len(survivor_delta),
        "owned_process_survivor_hashes": survivor_delta[:12],
        "profile_material_count": profile_material_count,
        "profile_material_persisted": profile_material_persisted,
        "terminal_receipt_count": terminal_receipt_count,
        "late_publication_blocked": True,
        "snapshot_hash": snapshot_hash,
        "target_origin_hash": target_origin_hash,
        "failure_code": failure_code,
        "exception_class_hash": exception_class_hash,
        "cycle_passed": cycle_passed,
        "duration_ms": int((time.monotonic() - started_at) * 1000),
    }


def _wait_for_baseline_restored(
    *,
    process_snapshotter: ProcessSnapshotter,
    baseline: BrowserProcessSnapshot,
    timeout_ms: int = 5_000,
) -> BrowserProcessSnapshot:
    deadline = time.monotonic() + (timeout_ms / 1000)
    last = process_snapshotter()
    while time.monotonic() < deadline:
        if not last.snapshot_error and not last.delta_from(baseline):
            return last
        time.sleep(0.2)
        last = process_snapshotter()
    return last


def _kill_process_tree(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        return
    try:
        os.kill(pid, 9)
    except Exception:
        return


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{ '1' }} else {{ '0' }}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return completed.stdout.strip() == "1"
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _default_engine_factory(cycle_root: Path, target_url: str, timeout_ms: int) -> RealBrowserEngine:
    previous = os.environ.get("SENTINEL_BROWSER_TEST_URL")
    try:
        os.environ["SENTINEL_BROWSER_TEST_URL"] = target_url
        engine = build_sentinel_chromium_real_browser_engine_from_env(capture_root=cycle_root)
        if hasattr(engine, "timeout_ms"):
            setattr(engine, "timeout_ms", timeout_ms)
        return engine
    finally:
        if previous is None:
            os.environ.pop("SENTINEL_BROWSER_TEST_URL", None)
        else:
            os.environ["SENTINEL_BROWSER_TEST_URL"] = previous


def _read_only_browser_authority(*, target_host: str) -> MissionAuthorityEnvelope:
    allowed_domains = [BOUNDED_URL_AUTHORITY_REF]
    if target_host:
        allowed_domains.append(target_host)
    return MissionAuthorityEnvelope(
        user_id="sentinel_c5_sovereign_physical_gate",
        mission_title="C5 sovereign browser physical gate",
        mission_objective="Verify the Sentinel-owned Chromium browser backend with bounded public read-only authority.",
        allowed_tools=["real_browser_control"],
        allowed_actions=[
            "real_browser.open",
            "real_browser.observe",
            "browser_session_open",
            "browser_session_observe",
            "browser_session_close",
        ],
        forbidden_actions=["login", "download", "upload", "payment", "contact", "credential_access"],
        allowed_domains=allowed_domains,
        max_actions=8,
    )


def _safe_origin_hash(url: str) -> str:
    parsed = urlparse(url)
    return stable_hash({"scheme": parsed.scheme.lower(), "host": (parsed.hostname or "").lower(), "port": parsed.port})


def _safe_failure_code(prefix: str, exc: Exception) -> str:
    if isinstance(exc, RealBrowserControlRuntimeError):
        value = str(exc).split(":", 1)[0].strip()
        if value:
            return value[:96]
    return f"{prefix}:{exc.__class__.__name__}"


def _profile_material_count(root: Path) -> int:
    if not root.exists():
        return 0
    count = 0
    for path in root.rglob("*"):
        if _is_profile_material_path(root, path):
            count += 1
    return count


def _is_profile_material_path(root: Path, path: Path) -> bool:
    try:
        parts = {part.lower() for part in path.relative_to(root).parts}
    except ValueError:
        return False
    return "profile" in parts or any(part in {"cookies", "local storage", "session storage", "indexeddb"} for part in parts)


def _remove_owned_tree(path: Path, owner_root: Path) -> None:
    resolved = path.resolve()
    owner = owner_root.resolve()
    try:
        resolved.relative_to(owner)
    except ValueError as exc:
        raise RuntimeError("owned_tree_escape_refused") from exc
    if resolved.exists():
        shutil.rmtree(resolved)


def _write_safe_bundle(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


__all__ = [
    "BrowserProcessSnapshot",
    "run_owned_stage_timeout_probe",
    "run_sentinel_chromium_sovereign_physical_gate",
    "snapshot_browser_processes",
    "summarize_sentinel_chromium_sovereign_boundary_probes",
]
