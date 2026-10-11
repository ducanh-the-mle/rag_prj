import chromadb
import redis
from minio import Minio
from .config import settings as s

redis_client = redis.Redis.from_url(s.redis_url, decode_responses=True)

minio_client = Minio(
    s.minio_endpoint,
    access_key=s.minio_access_key,
    secret_key=s.minio_secret_key,
    secure=False,
)


def get_chroma():
    return chromadb.HttpClient(host=s.chroma_host, port=s.chroma_port)