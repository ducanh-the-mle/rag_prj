from functools import lru_cache
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os 

load_dotenv()

MODEL = os.getenv("MODEL_NAME")

@lru_cache(maxsize=1)
def _model():
    return SentenceTransformer(MODEL)

def embed(texts: list[str]) -> list[list[str]]:
    return _model().encode(texts,normalize_embeddings=True).tolist()

