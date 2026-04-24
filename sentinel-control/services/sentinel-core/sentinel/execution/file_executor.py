from __future__ import annotations

from pathlib import Path

from sentinel.shared.models import AgentAction


class FileExecutor:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()

    def _resolve(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def create_folder(self, action: AgentAction) -> dict[str, str]:
        path_value = str(action.input.get("path") or action.input.get("folder_path") or "")
        path = self._resolve(path_value)
        path.mkdir(parents=True, exist_ok=True)
        return {"path": str(path), "status": "created"}

    def create_file(self, action: AgentAction) -> dict[str, str]:
        path_value = str(action.input.get("path") or action.input.get("file_path") or "")
        path = self._resolve(path_value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(action.input.get("content") or ""), encoding="utf-8")
        return {"path": str(path), "status": "created"}

