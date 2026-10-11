import io
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .chunking import chunk_text
from .clients import get_chroma, minio_client, redis_client
from .config import settings
from .embeddings import embed


def ensure_bucket(retries: int = 20):
    for _ in range(retries):
        try:
            if not minio_client.bucket_exists(settings.minio_bucket):
                minio_client.make_bucket(settings.minio_bucket)
            return
        except Exception:
            time.sleep(1.5)
    raise RuntimeError("Could not reach MinIO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    yield


app = FastAPI(title="RAG Pipeline", lifespan=lifespan)


def uploads_collection():
    return get_chroma().get_or_create_collection(
        "uploads", metadata={"hnsw:space": "cosine"}
    )


# ---------- UI ----------
@app.get("/")
def index():
    return FileResponse("app/static/index.html")


# ---------- health ----------
@app.get("/health")
def health():
    checks = {
        "redis": redis_client.ping,
        "chroma": lambda: get_chroma().heartbeat(),
        "minio": lambda: minio_client.bucket_exists(settings.minio_bucket),
    }
    status = {}
    for name, fn in checks.items():
        try:
            fn()
            status[name] = "ok"
        except Exception as e:
            status[name] = f"error: {e}"
    if any(v != "ok" for v in status.values()):
        raise HTTPException(503, status)
    return status


# ---------- upload ----------
class UploadIn(BaseModel):
    text: str = Field(min_length=1)


@app.post("/upload")
def upload(body: UploadIn):
    chunks = chunk_text(body.text)
    if not chunks:
        raise HTTPException(400, "No text found")

    doc_id = uuid.uuid4().hex[:8]

    # 1) keep the raw text in MinIO
    data = body.text.encode("utf-8")
    minio_client.put_object(
        settings.minio_bucket, f"uploads/{doc_id}.txt",
        io.BytesIO(data), len(data), content_type="text/plain",
    )

    # 2) store chunks + vectors in Chroma
    uploads_collection().add(
        ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=embed(chunks),
        metadatas=[{"doc_id": doc_id, "chunk": i} for i in range(len(chunks))],
    )
    return {"doc_id": doc_id, "chunks": len(chunks)}


# ---------- ask ----------
class AskIn(BaseModel):
    doc_id: str
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


@app.post("/ask")
def ask(body: AskIn):
    r = uploads_collection().query(
        query_embeddings=embed([body.question]),
        n_results=body.top_k,
        where={"doc_id": body.doc_id},
        include=["documents", "metadatas", "distances"],
    )
    return {
        "results": [
            {"chunk": m["chunk"], "score": round(1 - d, 3), "text": t}
            for t, m, d in zip(r["documents"][0], r["metadatas"][0], r["distances"][0])
        ]
    }