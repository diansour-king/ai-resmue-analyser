from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from .settings import get_settings


class StorageUnavailable(Exception):
    """The object store could not be reached or refused the operation.

    Raised in place of the botocore exception so nothing above this module has to import
    boto3, and so an endpoint URL carrying credentials never reaches an error handler.
    """


def original_key(resume_id: str) -> str:
    return f"resumes/{resume_id}/original.pdf"


def job_original_key(job_id: str) -> str:
    return f"jobs/{job_id}/original.pdf"


def page_render_key(resume_id: str, page_number: int) -> str:
    return f"resumes/{resume_id}/pages/{page_number:04d}.png"


@lru_cache
def _client() -> Any:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        # MinIO needs path-style addressing: the virtual-host style boto3 prefers would
        # resolve bucket.minio as a hostname that does not exist inside the compose network.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    settings = get_settings()
    try:
        _client().head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        try:
            _client().create_bucket(Bucket=settings.s3_bucket)
        except (ClientError, BotoCoreError) as exc:
            raise StorageUnavailable("could not create the bucket") from exc
    except BotoCoreError as exc:
        raise StorageUnavailable("could not reach the object store") from exc


def put(key: str, body: bytes, content_type: str) -> None:
    try:
        _client().put_object(
            Bucket=get_settings().s3_bucket, Key=key, Body=body, ContentType=content_type
        )
    except (ClientError, BotoCoreError) as exc:
        raise StorageUnavailable(f"could not store {key}") from exc


def get(key: str) -> bytes:
    try:
        response = _client().get_object(Bucket=get_settings().s3_bucket, Key=key)
        body: bytes = response["Body"].read()
    except (ClientError, BotoCoreError) as exc:
        raise StorageUnavailable(f"could not read {key}") from exc
    return body


def stream(key: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    """Yield an object in chunks so a page render never sits in memory twice.

    The API streams rather than redirecting to a presigned URL: a presigned URL is a
    credential the browser can keep and share, and access to a resume has to stay a decision
    this service makes on every request.
    """
    try:
        response = _client().get_object(Bucket=get_settings().s3_bucket, Key=key)
    except (ClientError, BotoCoreError) as exc:
        raise StorageUnavailable(f"could not read {key}") from exc
    body = response["Body"]
    try:
        while chunk := body.read(chunk_size):
            yield chunk
    finally:
        body.close()
