from types import SimpleNamespace

from app.services import storage


def test_s3_storage_configuration_constructs_client(monkeypatch) -> None:
    client_calls = []
    fake_boto3 = SimpleNamespace(client=lambda *args, **kwargs: client_calls.append((args, kwargs)) or object())
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: SimpleNamespace(
            storage_backend="s3",
            s3_endpoint_url="https://objects.example.test",
            s3_region="test-1",
            s3_bucket_name="novoriq-private",
            s3_access_key_id="access-key",
            s3_secret_access_key="secret-key",
            s3_use_ssl=True,
            s3_signed_url_ttl_seconds=300,
        ),
    )

    backend = storage.get_storage_backend()

    assert backend.bucket_name == "novoriq-private"
    assert client_calls[0][0] == ("s3",)
    assert client_calls[0][1]["endpoint_url"] == "https://objects.example.test"


def test_s3_storage_rejects_missing_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: SimpleNamespace(
            storage_backend="s3",
            s3_bucket_name="",
            s3_access_key_id="",
            s3_secret_access_key="",
        ),
    )

    try:
        storage.get_storage_backend()
    except RuntimeError as exc:
        assert str(exc) == "S3 storage requires bucket and access credentials."
    else:
        raise AssertionError("Missing S3 credentials must fail closed")
