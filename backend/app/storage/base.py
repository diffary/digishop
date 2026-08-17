from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def exists(self, key: str) -> bool: ...

    def path(self, key: str) -> Path: ...
