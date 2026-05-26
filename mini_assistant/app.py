import streamlit as st
import sqlite3
from datetime import datetime
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
import os
import numpy as np
import requests
from openai import OpenAI

st.set_page_config(page_title="智能问答助手", layout="wide")

class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ChromaClientManager(metaclass=SingletonMeta):
    def __init__(self):
        os.makedirs("./chroma_db", exist_ok=True)
        self.client = chromadb.Client(Settings(
            persist_directory="./chroma_db",
            anonymized_telemetry=False
        ))
    
    def get_client(self):
        return self.client

class EmbeddingModelManager(metaclass=SingletonMeta):
    def __init__(self):
        self.base_url = "http://localhost:11434/api/embeddings"
        self.model = "all-minilm"
        self.available = self._test_connection()
    
    def _test_connection(self):
        try:
            response = requests.post(
                self.base_url,
                json={"model": self.model, "prompt": "test"},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            self.error = f"嵌入模型不可用。请运行 'ollama pull {self.model}' 下载模型。错误: {str(e)}"
            return False
    
    def encode(self, texts):
        if not isinstance(texts, list):
            texts = [texts]
        
        try:
            embeddings = []
            for text in texts:
                response = requests.post(
                    self.base_url,
                    json={"model": self.model, "prompt": text},
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embedding", []))
            
            if embeddings and len(embeddings[0]) > 0:
                return np.array(embeddings)
            return None
        except Exception as e:
            self.error = str(e)
            return None
    
    def is_available(self):
        return self.available
    
    def get_error(self):
        return getattr(self, 'error', '未知错误')

class LLMClientManager(metaclass=SingletonMeta):
    DEFAULT_MODEL = "qwen3.6:27b"
    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    
    def __init__(self):
        self.model = self.DEFAULT_MODEL
        self.base_url = self.DEFAULT_BASE_URL
    
    def get_model(self):
        return self.model
    
    def generate_completion(self, prompt, max_tokens=2048, temperature=0.7):
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个智能助手，根据提供的上下文和知识回答用户的问题。"},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"模型调用失败: {str(e)}"

class DatabaseManager:
    _instance = None
    
    def __new__(cls, db_name='chat_history.db'):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize(db_name)
        return cls._instance
    
    def _initialize(self, db_name):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT '未命名对话',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def execute(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor
    
    def fetch_one(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def create_conversation(self, title='未命名对话'):
        cursor = self.execute(
            'INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)',
            (title, datetime.now().isoformat(), datetime.now().isoformat())
        )
        return cursor.lastrowid
    
    def get_conversations(self):
        return self.fetch_all('SELECT * FROM conversations ORDER BY updated_at DESC')
    
    def get_conversation(self, conv_id):
        return self.fetch_one('SELECT * FROM conversations WHERE id = ?', (conv_id,))
    
    def update_conversation(self, conv_id, title):
        self.execute(
            'UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?',
            (title, datetime.now().isoformat(), conv_id)
        )
    
    def delete_conversation(self, conv_id):
        self.execute('DELETE FROM messages WHERE conversation_id = ?', (conv_id,))
        self.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
    
    def add_message(self, conv_id, role, content):
        self.execute(
            'INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)',
            (conv_id, role, content, datetime.now().isoformat())
        )
        self.execute(
            'UPDATE conversations SET updated_at = ? WHERE id = ?',
            (datetime.now().isoformat(), conv_id)
        )
    
    def get_messages(self, conv_id):
        return self.fetch_all(
            'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
            (conv_id,)
        )
    
    def add_knowledge_file(self, filename, content):
        self.execute(
            'INSERT INTO knowledge_files (filename, content, created_at) VALUES (?, ?, ?)',
            (filename, content, datetime.now().isoformat())
        )
    
    def get_knowledge_files(self):
        return self.fetch_all('SELECT * FROM knowledge_files ORDER BY created_at DESC')
    
    def delete_knowledge_file(self, file_id):
        self.execute('DELETE FROM knowledge_files WHERE id = ?', (file_id,))

class KnowledgeBase:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeBase, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.chroma_client = ChromaClientManager().get_client()
        self.embedding_manager = EmbeddingModelManager()
        self.collection = self.chroma_client.get_or_create_collection(name="knowledge")
        self.chunk_size = 512
        self.chunk_overlap = 50
    
    def is_embedding_available(self):
        return self.embedding_manager.is_available()
    
    def get_embedding_error(self):
        return self.embedding_manager.get_error()
    
    def chunk_text(self, text):
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        return chunks
    
    def add_document(self, filename, content):
        if not self.is_embedding_available():
            return -1
        
        chunks = self.chunk_text(content)
        if not chunks:
            return 0
        
        embeddings = self.embedding_manager.encode(chunks)
        if embeddings is None:
            return -1
        
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"filename": filename, "chunk_index": i} for i in range(len(chunks))]
        
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return len(chunks)
    
    def recall(self, query, top_k=10):
        if not self.is_embedding_available():
            return {'documents': [[]], 'metadatas': [[]]}
        
        query_embedding = self.embedding_manager.encode(query)
        if query_embedding is None:
            return {'documents': [[]], 'metadatas': [[]]}
        
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k
        )
        return results
    
    def rerank(self, query, documents, top_n=5):
        if len(documents) == 0:
            return []
        
        tokenized_docs = [doc.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)
        
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, score in scored_docs[:top_n]]
    
    def search(self, query, top_k=10, rerank_top_n=5):
        recall_results = self.recall(query, top_k)
        
        if not recall_results['documents'] or len(recall_results['documents'][0]) == 0:
            return []
        
        documents = recall_results['documents'][0]
        metadatas = recall_results['metadatas'][0]
        
        reranked_docs = self.rerank(query, documents, rerank_top_n)
        
        final_results = []
        for doc in reranked_docs:
            idx = documents.index(doc)
            final_results.append({
                'content': doc,
                'filename': metadatas[idx]['filename'],
                'chunk_index': metadatas[idx]['chunk_index']
            })
        
        return final_results
    
    def get_document_count(self):
        return self.collection.count()
    
    def clear_all(self):
        self.chroma_client.delete_collection(name="knowledge")
        self.collection = self.chroma_client.create_collection(name="knowledge")

class ChatSessionManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.kb = KnowledgeBase()
        self.llm_client = LLMClientManager()
    
    def init_session_state(self):
        if 'current_conversation' not in st.session_state:
            st.session_state['current_conversation'] = None
        if 'messages' not in st.session_state:
            st.session_state['messages'] = []
        if 'show_settings' not in st.session_state:
            st.session_state['show_settings'] = False
    
    def load_conversation(self, conv_id):
        st.session_state['current_conversation'] = conv_id
        messages = self.db.get_messages(conv_id)
        st.session_state['messages'] = [{'role': m[2], 'content': m[3]} for m in messages]
        
        conv = self.db.get_conversation(conv_id)
        if conv:
            st.session_state['conversation_title'] = conv[1]
    
    def save_message(self, role, content):
        if st.session_state['current_conversation'] is None:
            conv_id = self.db.create_conversation()
            st.session_state['current_conversation'] = conv_id
        
        self.db.add_message(st.session_state['current_conversation'], role, content)
        st.session_state['messages'].append({'role': role, 'content': content})
        
        if role == 'user' and len(st.session_state['messages']) == 1:
            title = content[:30] + '...' if len(content) > 30 else content
            self.db.update_conversation(st.session_state['current_conversation'], title)
    
    def generate_response(self, query):
        if self.kb.is_embedding_available():
            knowledge_results = self.kb.search(query)
            context = "\n\n".join([f"【{result['filename']}】\n{result['content']}" for result in knowledge_results])
            
            if context:
                prompt = f"基于以下知识库内容回答问题：\n\n{context}\n\n问题：{query}\n\n请根据知识库内容回答，如果知识库中没有相关信息，请直接说明。"
            else:
                prompt = f"回答以下问题：{query}"
        else:
            prompt = f"回答以下问题：{query}\n\n（注：知识库检索功能暂不可用）"
        
        return self.llm_client.generate_completion(prompt)

class UIManager:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.db = session_manager.db
        self.kb = session_manager.kb
    
    def render_sidebar(self):
        with st.sidebar:
            st.title("🤖 智能问答助手")
            st.markdown("---")
            
            st.subheader("会话列表")
            conversations = self.db.get_conversations()
            
            if conversations:
                for conv in conversations:
                    conv_id, title, created_at, updated_at = conv
                    is_active = st.session_state['current_conversation'] == conv_id
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(title, key=f"conv_{conv_id}", 
                                    use_container_width=True,
                                    type="primary" if is_active else "secondary"):
                            self.session_manager.load_conversation(conv_id)
                    with col2:
                        if st.button("🗑️", key=f"del_{conv_id}", help="删除会话"):
                            self.db.delete_conversation(conv_id)
                            if st.session_state['current_conversation'] == conv_id:
                                st.session_state['current_conversation'] = None
                                st.session_state['messages'] = []
                            st.rerun()
            else:
                st.info("暂无会话，开始新对话吧！")
            
            if st.button("➕ 新建会话", use_container_width=True):
                conv_id = self.db.create_conversation()
                self.session_manager.load_conversation(conv_id)
            
            st.markdown("---")
            
            if st.button("⚙️ 知识库管理", use_container_width=True):
                st.session_state['show_settings'] = True
    
    def render_main_chat(self):
        if st.session_state['current_conversation'] is None:
            st.info("👋 欢迎使用智能问答助手！\n\n请在左侧新建会话开始提问。")
            if not self.kb.is_embedding_available():
                st.warning(f"⚠️ 知识库检索功能暂不可用：{self.kb.get_embedding_error()}\n\n问答功能仍可使用，但无法检索上传的知识库文档。")
            return
        
        st.title(st.session_state.get('conversation_title', '未命名对话'))
        
        if not self.kb.is_embedding_available():
            st.warning(f"⚠️ 知识库检索功能暂不可用：{self.kb.get_embedding_error()}")
        
        for msg in st.session_state['messages']:
            with st.chat_message(msg['role']):
                st.write(msg['content'])
        
        if prompt := st.chat_input("请输入您的问题..."):
            with st.chat_message('user'):
                st.write(prompt)
            
            self.session_manager.save_message('user', prompt)
            
            with st.chat_message('assistant'):
                with st.spinner("正在思考..."):
                    response = self.session_manager.generate_response(prompt)
                    st.write(response)
            
            self.session_manager.save_message('assistant', response)
    
    def render_knowledge_management(self):
        st.title("📚 知识库管理")
        
        if not self.kb.is_embedding_available():
            st.error(f"❌ 嵌入模型不可用: {self.kb.get_embedding_error()}")
            st.info("请确保已连接到互联网以下载模型，或使用已缓存的模型。")
            if st.button("← 返回对话", use_container_width=True):
                st.session_state['show_settings'] = False
            return
        
        tab1, tab2 = st.tabs(["上传文件", "已上传文件"])
        
        with tab1:
            st.subheader("上传文档")
            st.markdown("支持上传文本文件（.txt），文件内容将被分割并存储到向量库中。")
            
            uploaded_files = st.file_uploader("选择文件", type=['txt'], accept_multiple_files=True)
            
            if uploaded_files:
                for file in uploaded_files:
                    content = file.read().decode('utf-8')
                    
                    with st.spinner(f"正在处理 {file.name}..."):
                        chunk_count = self.kb.add_document(file.name, content)
                        if chunk_count == -1:
                            st.error(f"❌ 处理文件 '{file.name}' 失败：嵌入模型不可用")
                            continue
                        self.db.add_knowledge_file(file.name, content)
                    
                    st.success(f"✅ 文件 '{file.name}' 上传成功！共分割为 {chunk_count} 个片段")
            
            st.markdown("---")
            st.subheader("向量库统计")
            doc_count = self.kb.get_document_count()
            st.metric("向量库文档数", doc_count)
            
            if st.button("清空知识库", type="secondary", use_container_width=True):
                if st.session_state.get('confirm_clear'):
                    self.kb.clear_all()
                    st.success("知识库已清空")
                    st.session_state['confirm_clear'] = False
                else:
                    st.warning("⚠️ 此操作将删除所有知识库内容，再次点击确认")
                    st.session_state['confirm_clear'] = True
        
        with tab2:
            st.subheader("已上传文件列表")
            files = self.db.get_knowledge_files()
            
            if files:
                for file in files:
                    file_id, filename, content, created_at = file
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{filename}**")
                        st.caption(f"上传时间: {created_at}")
                        st.caption(f"内容长度: {len(content)} 字符")
                    with col2:
                        if st.button("删除", key=f"kb_del_{file_id}"):
                            self.db.delete_knowledge_file(file_id)
                            st.rerun()
            else:
                st.info("暂无上传的文件")
        
        if st.button("← 返回对话", use_container_width=True):
            st.session_state['show_settings'] = False
    
    def render(self):
        self.session_manager.init_session_state()
        
        if st.session_state.get('show_settings'):
            self.render_knowledge_management()
        else:
            self.render_sidebar()
            self.render_main_chat()

def main():
    session_manager = ChatSessionManager()
    ui_manager = UIManager(session_manager)
    ui_manager.render()

if __name__ == '__main__':
    main()