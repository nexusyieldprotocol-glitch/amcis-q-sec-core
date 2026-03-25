"""
AMCIS Redis Manager
===================

Handles Pub/Sub and caching for real-time event streaming between 
AMCIS Q-Sec-Core modules and the API Gateway.
"""

import os
import json
import redis
import structlog
from typing import Any, Callable, Dict, Optional

class RedisManager:
    """
    Manages Redis connections and Pub/Sub operations.
    """
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_url = os.environ.get("REDIS_URL", f"redis://{host}:{port}/{db}")
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        self.logger = structlog.get_logger("amcis.redis")
        self.pubsub = self.client.pubsub()

    def publish_event(self, channel: str, data: Dict[str, Any]):
        """Publish an event to a specific Redis channel."""
        try:
            self.client.publish(channel, json.dumps(data))
            self.logger.debug("event_published", channel=channel)
        except Exception as e:
            self.logger.error("publish_failed", error=str(e))

    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to a channel and execute a callback on message."""
        self.pubsub.subscribe(**{channel: lambda msg: callback(json.loads(msg['data']))})
        self.logger.info("subscribed_to_channel", channel=channel)

    def start_listening(self):
        """Start the background thread for listening to messages."""
        self.pubsub.run_in_thread(sleep_time=0.01)

    def set_cache(self, key: str, value: Any, ex: int = 3600):
        """Set a value in the Redis cache."""
        self.client.set(key, json.dumps(value), ex=ex)

    def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from the Redis cache."""
        data = self.client.get(key)
        return json.loads(data) if data else None
