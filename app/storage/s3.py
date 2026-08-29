import logging
from typing import Any

import aioboto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3ObjectStorage:
    def __init__(self) -> None:
        self._context: Any | None = None
        self._client: Any | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def connect(self) -> None:
        if self._client is not None:
            return
        config = settings.object_storage
        self._context = aioboto3.Session().client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key.get_secret_value(),
            region_name=config.region,
            config=Config(signature_version="s3v4"),
        )
        self._client = await self._context.__aenter__()
        try:
            await self._client.head_bucket(Bucket=config.bucket)
        except self._client.exceptions.ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                await self.close()
                raise
            await self._client.create_bucket(Bucket=config.bucket)
        logger.info("Object storage connected: bucket=%s", config.bucket)

    async def close(self) -> None:
        context, self._context, self._client = self._context, None, None
        if context is not None:
            await context.__aexit__(None, None, None)
        logger.info("Object storage disconnected")

    async def upload(self, object_key: str, content: bytes, content_type: str) -> None:
        logger.debug("Uploading attachment: key=%s, size=%d", object_key, len(content))
        await self._require_client().put_object(
            Bucket=settings.object_storage.bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )

    async def download(self, object_key: str) -> bytes:
        logger.debug("Downloading attachment: key=%s", object_key)
        response = await self._require_client().get_object(
            Bucket=settings.object_storage.bucket,
            Key=object_key,
        )
        async with response["Body"] as stream:
            return bytes(await stream.read())

    async def delete(self, object_key: str) -> None:
        logger.debug("Deleting attachment: key=%s", object_key)
        await self._require_client().delete_object(
            Bucket=settings.object_storage.bucket,
            Key=object_key,
        )

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Object storage is not connected")
        return self._client


object_storage = S3ObjectStorage()
