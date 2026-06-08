import numpy as np
from typing import List, Union
import logging
import os

logger = logging.getLogger(__name__)

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from sentence_transformers import SentenceTransformer, CrossEncoder
logger.info("sentence-transformers imported successfully")


class EmbeddingModel:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        logger.info(f"Loading embedding model: {self.model_name}")
        self._model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded successfully")

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        if normalize and embeddings.shape[0] > 0:
            norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norm + 1e-10)

        return embeddings

    def get_dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()


class RerankerModel:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._available = False
        self._load_model()

    def _load_model(self):
        try:
            logger.info(f"Loading reranker model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            self._available = True
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load reranker model: {e}")
            logger.warning("Reranking will be disabled")

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[dict]:
        if not self._available:
            return [{'index': i, 'document': doc, 'score': 1.0} for i, doc in enumerate(documents[:top_k])]

        try:
            scores = self._model.predict([(query, doc) for doc in documents])
            scored_docs = [(i, doc, float(score)) for i, (doc, score) in enumerate(zip(documents, scores))]
            scored_docs.sort(key=lambda x: x[2], reverse=True)
            
            return [{'index': i, 'document': doc, 'score': score} for i, doc, score in scored_docs[:top_k]]
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return [{'index': i, 'document': doc, 'score': 1.0} for i, doc in enumerate(documents[:top_k])]
