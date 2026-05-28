# 智能问答系统 (RAG-based Q&A System)

基于Streamlit和RAG技术的智能问答应用，支持文档上传、向量化存储和知识库检索。

## 技术栈

- **Streamlit**: Web UI框架
- **FAISS**: 高效向量相似度搜索
- **Sentence Transformers**: 文本嵌入和重排模型
- **Ollama**: 本地大模型服务 (qwen3.6:27b)
- **LangChain**: RAG流程编排

## 核心功能

- 📄 **文档上传**: 支持 PDF、DOCX、TXT、Excel 格式
- 🔍 **智能检索**: Recall + ReRank 两阶段检索
- 🤖 **大模型问答**: 基于本地 qwen3.6:27b 模型
- 💾 **向量存储**: FAISS 高性能向量索引
- 💬 **对话历史**: 支持多轮对话

## 安装依赖

```bash
cd mini_assistant
pip install -r requirements.txt
```

## 启动 Ollama 服务

确保 Ollama 服务正在运行，并且 qwen3.6:27b 模型已下载：

```bash
ollama run qwen3.6:27b
```

或者启动 Ollama 服务：

```bash
ollama serve
```

## 启动应用

```bash
streamlit run app.py
```

应用将在浏览器中打开，通常为 http://localhost:8501

## 使用流程

1. **上传文档**: 在侧边栏上传需要建立知识库的文档
2. **等待处理**: 系统会自动将文档分块、向量化并存储
3. **开始问答**: 在输入框中输入问题，系统会基于知识库进行回答
4. **查看来源**: 可以展开查看回答的参考来源

## 配置说明

在 `config.py` 中可以修改以下配置：

- `OLLAMA_MODEL`: 大模型名称 (默认: qwen3.6:27b)
- `OLLAMA_BASE_URL`: Ollama 服务地址 (默认: http://localhost:11434/v1)
- `EMBEDDING_MODEL_NAME`: 嵌入模型名称
- `RERANK_MODEL_NAME`: 重排模型名称
- `CHUNK_SIZE`: 文档分块大小 (默认: 500字符)
- `CHUNK_OVERLAP`: 分块重叠大小 (默认: 50字符)

## 项目结构

```
mini_assistant/
├── app.py                 # Streamlit 主应用
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── rag.py                 # 模块导出
├── document_processor.py  # 文档处理模块
├── embeddings.py         # 嵌入和重排模型
├── vector_store.py       # FAISS 向量存储
├── retriever.py          # 检索器 (Recall + ReRank)
├── llm.py                # LLM 客户端
├── rag_engine.py         # RAG 引擎整合
└── uploads/              # 上传的文档
└── vector_store/         # 向量索引存储
```

## RAG 流程说明

1. **文档处理**: 将上传的文档解析为文本，并按设定大小分块
2. **向量化**: 使用 Sentence Transformers 将文本块转为向量
3. **存储**: 使用 FAISS 建立向量索引并持久化
4. **Recall**: 根据用户问题，从向量库中召回最相关的文档块
5. **ReRank**: 使用 Cross-Encoder 对召回结果进行重排
6. **生成**: 将 top-k 相关文档作为上下文，调用 LLM 生成回答

## 注意事项

- 确保 Ollama 服务正在运行
- 首次运行会下载嵌入模型和重排模型
- 知识库变更后会自动保存
- 支持多文件同时上传
