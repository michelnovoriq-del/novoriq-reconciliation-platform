from app.config import get_settings
from app.services.storage.base import StorageBackend
from app.services.storage.local_storage import LocalStorage
from app.services.storage.s3_storage import S3Storage


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorage(settings.upload_dir)
    if settings.storage_backend == "s3":
        if not (
            settings.s3_bucket_name
            and settings.s3_access_key_id
            and settings.s3_secret_access_key
        ):
            raise RuntimeError("S3 storage requires bucket and access credentials.")
        return S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            region=settings.s3_region,
            bucket_name=settings.s3_bucket_name,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            use_ssl=settings.s3_use_ssl,
            signed_url_ttl_seconds=settings.s3_signed_url_ttl_seconds,
        )
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")
