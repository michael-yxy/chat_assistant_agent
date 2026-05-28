from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from document_processor import DocumentProcessor
from embeddings import EmbeddingModel, RerankerModel
from vector_store import VectorStore
from retriever import Retriever
from llm import LLMClient
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        rerank_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        llm_base_url: str = "http://localhost:11434/v1",
        llm_model: str = "qwen3.6:35b-a3b-q8_0",
        vector_store_path: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.doc_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        logger.info("Initializing embedding model...")
        self.embedding_model = EmbeddingModel(model_name=embedding_model_name)

        logger.info("Initializing reranker model...")
        try:
            self.reranker_model = RerankerModel(model_name=rerank_model_name)
        except Exception as e:
            logger.warning(f"Failed to load reranker model: {e}. Reranking will be disabled.")
            self.reranker_model = None

        embedding_dim = self.embedding_model.get_dimension()
        self.vector_store = VectorStore(
            embedding_dim=embedding_dim,
            store_path=vector_store_path
        )

        self.retriever = Retriever(
            vector_store=self.vector_store,
            embedding_model=self.embedding_model,
            reranker_model=self.reranker_model
        )

        logger.info("Initializing LLM client...")
        self.llm_client = LLMClient(
            base_url=llm_base_url,
            model=llm_model
        )
        
        # 保存配置
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model

    def update_llm_config(self, base_url: str, model: str) -> Dict:
        """更新LLM配置"""
        try:
            # 创建新的LLM客户端
            new_client = LLMClient(
                base_url=base_url,
                model=model
            )
            
            # 测试连接
            test_result = new_client.test_connection()
            
            if test_result["success"]:
                # 关闭旧客户端，替换为新的
                self.llm_client.close()
                self.llm_client = new_client
                self.llm_base_url = base_url
                self.llm_model = model
                
                logger.info(f"LLM config updated to: base_url={base_url}, model={model}")
                return {
                    "success": True,
                    "message": test_result["message"],
                    "status": "updated"
                }
            else:
                new_client.close()
                return test_result
                
        except Exception as e:
            logger.error(f"Failed to update LLM config: {e}")
            return {
                "success": False,
                "message": f"❌ 更新配置失败: {str(e)}",
                "status": "error"
            }

    def test_current_connection(self) -> Dict:
        """测试当前配置的连接"""
        return self.llm_client.test_connection()
    
    def test_model_connection(self, model_name: str) -> Dict:
        """测试指定模型的连接"""
        return self.llm_client.test_connection(model_name=model_name)

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return self.llm_client.get_available_models()

    def add_documents(self, file_paths: List[Path]) -> Dict:
        total_chunks = 0
        successful_files = []
        failed_files = []

        for file_path in file_paths:
            try:
                documents = self.doc_processor.process_file(file_path)

                if documents:
                    embeddings = self.embedding_model.encode(
                        [doc['content'] for doc in documents]
                    )

                    self.vector_store.add_documents(embeddings, documents)
                    total_chunks += len(documents)
                    successful_files.append(file_path.name)

                    logger.info(f"Added {len(documents)} chunks from {file_path.name}")
                else:
                    failed_files.append(file_path.name)

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                failed_files.append(file_path.name)

        self.vector_store.save()

        return {
            'total_chunks': total_chunks,
            'successful_files': successful_files,
            'failed_files': failed_files
        }

    def query(
        self,
        question: str,
        recall_top_k: int = 20,
        rerank_top_k: int = 5,
        use_rerank: bool = True
    ) -> Dict:
        stats = self.vector_store.get_stats()
        has_knowledge_base = stats['total_documents'] > 0
        
        thinking_steps = []

        if has_knowledge_base:
            thinking_steps.append(f"🧠 分析问题: {question}")
            thinking_steps.append(f"📚 知识库中有 {stats['total_documents']} 个文档，{stats['index_size']} 个片段")
            thinking_steps.append(f"🔍 正在检索相关文档... (Recall: top-{recall_top_k})")
            
            retrieved_docs = self.retriever.retrieve(
                query=question,
                recall_top_k=recall_top_k,
                rerank_top_k=rerank_top_k if use_rerank else recall_top_k
            )

            if retrieved_docs:
                if use_rerank:
                    thinking_steps.append(f"⚡ 正在进行重排... (ReRank: top-{rerank_top_k})")
                thinking_steps.append(f"✅ 检索到 {len(retrieved_docs)} 篇相关文档")
                thinking_steps.append(f"📖 正在阅读文档并生成回答...")
                
                contexts = [doc['content'] for doc in retrieved_docs]
                answer = self.llm_client.generate_with_context(
                    query=question,
                    context=contexts
                )

                return {
                    'answer': answer,
                    'sources': [
                        {
                            'content': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                            'source': doc['metadata']['source'],
                            'score': doc.get('rerank_score', doc.get('distance', 0))
                        }
                        for doc in retrieved_docs
                    ],
                    'contexts': contexts,
                    'mode': 'rag',
                    'thinking': thinking_steps
                }
            else:
                thinking_steps.append("⚠️ 知识库中未找到相关文档，切换到对话模式")

        thinking_steps.append("💬 使用大模型直接回答...")
        answer = self.llm_client.chat(query=question)

        return {
            'answer': answer,
            'sources': [],
            'contexts': [],
            'mode': 'chat',
            'thinking': thinking_steps
        }
    
    def query_stream(
        self,
        question: str,
        recall_top_k: int = 20,
        rerank_top_k: int = 5,
        use_rerank: bool = True
    ):
        """流式查询，返回生成器"""
        stats = self.vector_store.get_stats()
        has_knowledge_base = stats['total_documents'] > 0

        if has_knowledge_base:
            retrieved_docs = self.retriever.retrieve(
                query=question,
                recall_top_k=recall_top_k,
                rerank_top_k=rerank_top_k if use_rerank else recall_top_k
            )

            if retrieved_docs:
                contexts = [doc['content'] for doc in retrieved_docs]
                yield {
                    'type': 'sources',
                    'data': [
                        {
                            'content': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                            'source': doc['metadata']['source'],
                            'score': doc.get('rerank_score', doc.get('distance', 0))
                        }
                        for doc in retrieved_docs
                    ],
                    'contexts': contexts,
                    'mode': 'rag'
                }
                
                # 流式生成回答
                for chunk in self.llm_client.generate_with_context_stream(
                    query=question,
                    context=contexts
                ):
                    yield {
                        'type': 'answer_chunk',
                        'data': chunk,
                        'mode': 'rag'
                    }
                return

        # 对话模式流式回答
        yield {
            'type': 'sources',
            'data': [],
            'contexts': [],
            'mode': 'chat'
        }
        
        for chunk in self.llm_client.chat_stream(query=question):
            yield {
                'type': 'answer_chunk',
                'data': chunk,
                'mode': 'chat'
            }
    
    def query(
        self,
        question: str,
        recall_top_k: int = 20,
        rerank_top_k: int = 5,
        use_rerank: bool = True
    ) -> Dict:
        """非流式查询，返回完整结果"""
        stats = self.vector_store.get_stats()
        has_knowledge_base = stats['total_documents'] > 0
        
        thinking_steps = []

        if has_knowledge_base:
            thinking_steps.append(f"🧠 分析问题: {question}")
            thinking_steps.append(f"📚 知识库中有 {stats['total_documents']} 个文档，{stats['index_size']} 个片段")
            thinking_steps.append(f"🔍 正在检索相关文档... (Recall: top-{recall_top_k})")
            
            retrieved_docs = self.retriever.retrieve(
                query=question,
                recall_top_k=recall_top_k,
                rerank_top_k=rerank_top_k if use_rerank else recall_top_k
            )

            if retrieved_docs:
                if use_rerank:
                    thinking_steps.append(f"⚡ 正在进行重排... (ReRank: top-{rerank_top_k})")
                thinking_steps.append(f"✅ 检索到 {len(retrieved_docs)} 篇相关文档")
                thinking_steps.append(f"📖 正在阅读文档并生成回答...")
                
                contexts = [doc['content'] for doc in retrieved_docs]
                answer = self.llm_client.generate_with_context(
                    query=question,
                    context=contexts
                )

                return {
                    'answer': answer,
                    'sources': [
                        {
                            'content': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                            'source': doc['metadata']['source'],
                            'score': doc.get('rerank_score', doc.get('distance', 0))
                        }
                        for doc in retrieved_docs
                    ],
                    'contexts': contexts,
                    'mode': 'rag',
                    'thinking': thinking_steps
                }
            else:
                thinking_steps.append("⚠️ 知识库中未找到相关文档，切换到对话模式")

        thinking_steps.append("💬 使用大模型直接回答...")
        answer = self.llm_client.chat(query=question)

        return {
            'answer': answer,
            'sources': [],
            'contexts': [],
            'mode': 'chat',
            'thinking': thinking_steps
        }

    def get_stats(self) -> Dict:
        return self.vector_store.get_stats()

    def reset(self):
        self.vector_store.index = None
        self.vector_store.documents = []
        self.vector_store.metadata = []
        self.vector_store.save()