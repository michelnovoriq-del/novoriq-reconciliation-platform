from pathlib import Path

from app.services.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(
        self,
        *,
        endpoint_url: str | None,
        region: str | None,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        use_ssl: bool,
        signed_url_ttl_seconds: int,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use STORAGE_BACKEND=s3.") from exc
        self.bucket_name = bucket_name
        self.signed_url_ttl_seconds = signed_url_ttl_seconds
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            use_ssl=use_ssl,
        )

    def save_file(self, source_path: Path, object_key: str) -> str:
        self.client.upload_file(
            str(source_path),
            self.bucket_name,
            object_key,
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
        source_path.unlink(missing_ok=True)
        return object_key

    def open_file(self, object_key: str):
        response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
        return response["Body"]

    def delete_file(self, object_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def file_exists(self, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except Exception:
            return False

    def generate_authorized_download_url(self, object_key: str) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=self.signed_url_ttl_seconds,
        )
