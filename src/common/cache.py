from __future__ import absolute_import, annotations

from typing import Optional

from wenet.common.storage.cache import RedisCache


class BotCache(RedisCache):

    def cache(self, data: dict, ttl: int = 604800, key: Optional[str] = None) -> str:
        return super().cache(data, ttl, key)

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
