from pathlib import Path

from app.storage.base import Storage

# app/storage/local.py -> app/storage -> app -> backend (parent.parent.parent).
# Existing file_keys already carry the "files/" prefix (e.g. "files/demo.zip"),
# so root must land on backend/, NOT backend/files/.
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or _DEFAULT_ROOT).resolve()

    def _resolve(self, key: str) -> Path:
        resolved = (self.root / key).resolve()
        # ключ обязан оставаться внутри root/files/ — иначе file_key вида
        # "files/../.env" мог бы отдать секреты бэкенда (находка ревью Task 8)
        if not resolved.is_relative_to(self.root / "files"):
            raise ValueError(f"path traversal detected for key: {key!r}")
        return resolved

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def path(self, key: str) -> Path:
        return self._resolve(key)


def get_storage() -> Storage:
    return LocalStorage()
