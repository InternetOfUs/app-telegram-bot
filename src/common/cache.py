from __future__ import absolute_import, annotations

from typing import Optional

from wenet.storage.cache import RedisCache


class BotCache(RedisCache):

    def cache(self, data: dict, ttl: int = 604800, key: Optional[str] = None) -> str:
        return super().cache(data, key, ttl=ttl)

    @staticmethod
    def build_from_env() -> BotCache:
        """
        Build the bot cache using environment variables.

        Required environment variables are:
          - REDIS_HOST - default to 'localhost'
          - REDIS_PORT - default to '6379'
          - REDIS_DB - default to '0'

        :return: the bot cache
        """
        r = BotCache._build_redis_from_env()
        return BotCache(r)

    def remove(self, key: str):
        """
        Remove a key and its value from the cache
        """
        self._r.delete(key)
