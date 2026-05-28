import os
from pathlib import Path

# 设置国内镜像源
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
MODELS_DIR = BASE_DIR / "models"

for dir_path in [UPLOAD_DIR, VECTOR_STORE_DIR, MODELS_DIR]:
    dir_path.mkdir(exist_ok=True)

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen3.6:35b-a3b-q8_0"
OLLAMA_API_KEY = "ollama"

# 使用主流的sentence-transformers模型（通过国内镜像下载）
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

RECALL_TOP_K = 20
RERANK_TOP_K = 5