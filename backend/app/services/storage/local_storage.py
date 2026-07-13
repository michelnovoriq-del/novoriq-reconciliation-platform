import shutil
from pathlib import Path

from app.services.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, object_key: str) -> Path:
        path = (self.root / object_key).resolve()
        root = self.root.resolve()
        if root not in path.parents and path != root:
            raise ValueError("Invalid storage object key.")
        return path

    def save_file(self, source_path: Path, object_key: str) -> str:
        target = self._path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), target)
        return str(target)

    def open_file(self, object_key: str):
        return self._path(object_key).open("rb")

    def delete_file(self, object_key: str) -> None:
        path = self._path(object_key)
        if path.exists():
            path.unlink()

    def file_exists(self, object_key: str) -> bool:
        return self._path(object_key).exists()

    def generate_authorized_download_url(self, object_key: str) -> str | None:
        return None
