from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, source_path: Path, object_key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def open_file(self, object_key: str):
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, object_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_authorized_download_url(self, object_key: str) -> str | None:
        raise NotImplementedError
