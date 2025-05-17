import redis
from luna.settings import REDIS_HOST, REDIS_PORT

redis_instance = redis.StrictRedis(
    host=REDIS_HOST, 
    port=REDIS_PORT,
    db=1,
    decode_responses=True
)
