from enum import StrEnum
from urllib.parse import quote


class CacheNamespace(StrEnum):
    SCHEDULE_DAY = "schedule-day"
    SCHEDULE_WEEK = "schedule-week"
    HOMEWORK = "homework"
    HOMEWORK_LIST = "homework-list"
    HOMEWORK_HISTORY = "homework-history"


class CacheKeyBuilder:
    def __init__(self, prefix: str, version: str = "v1") -> None:
        self._prefix = self._encode(prefix)
        self._version = self._encode(version)

    def build(self, namespace: CacheNamespace, *parts: object) -> str:
        segments = (self._prefix, self._version, namespace.value, *map(self._encode, parts))
        return ":".join(segments)

    def pattern(self, namespace: CacheNamespace, *parts: object) -> str:
        return f"{self.build(namespace, *parts)}:*"

    @staticmethod
    def _encode(value: object) -> str:
        return quote(str(value), safe="-_.")
