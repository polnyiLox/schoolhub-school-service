from abc import ABC, abstractmethod


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    async def set(
        self,
        key: str,
        value: str | bytes,
        ttl_seconds: int | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *keys: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        raise NotImplementedError
