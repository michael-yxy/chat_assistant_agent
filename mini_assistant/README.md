# 智能对话助理智能体（RAG-based Chat Assistant Agent）

基于 Streamlit 和 RAG 技术的智能问答系统，支持多知识库管理、文档上传、向量化存储、知识库检索和联网搜索等功能。

## 技术栈

- **Streamlit**: Web UI 框架
- **FAISS**: 高效向量相似度搜索
- **Sentence Transformers**: 文本嵌入和重排模型
- **Ollama**: 本地大模型服务
- **BAAI/bge-m3**: 嵌入模型（多模态嵌入，支持文本、图像、语音）
- **BAAI/bge-reranker-v2-m3**: 重排模型（提升检索精度）
- **Hugging Face**: 模型下载（国内通过 hf-mirror 加速）
- **KKFileView**: 在线文件预览服务（Docker）
- **Docker**: 容器化部署

## 核心功能

### 🤖 智能问答
- 基于本地大模型的对话功能
- 支持多轮对话上下文理解
- 实时流式响应
- 思考过程展示

### 📚 知识库管理
- **多知识库支持**: 创建和管理多个独立知识库
- **文档上传**: 支持 PDF、DOCX、TXT、Excel 格式
- **智能检索**: Recall + ReRank 两阶段检索
- **向量存储**: FAISS 高性能向量索引
- **文档/片段预览**: 查看上传的文档和向量化后的片段
- **知识库配置**: 可配置分块大小、重叠大小、召回数量、重排数量

### 🌐 联网搜索
- 集成网络搜索功能
- 支持配置搜索结果数量
- 搜索结果与知识库结果混合展示

### 💬 会话管理
- 新建和切换会话
- 会话历史自动保存
- 删除会话功能
- 会话侧栏可折叠

### ⚙️ LLM 配置
- 动态配置 Ollama 服务地址
- 支持选择可用模型
- 连接测试功能

### 📊 用户反馈
- 回答点赞/点踩功能
- 回答一键复制
- 反馈历史查看

## 安装依赖

```bash
cd mini_assistant
pip install -r requirements.txt
```

## 启动 Ollama 服务

确保 Ollama 服务正在运行，并且已下载所需模型：

```bash
# 启动 Ollama 服务
ollama serve

# 或直接运行模型（首次运行会自动下载）
ollama run qwen3.6:35b-a3b-q8_0
```

## 启动 KKFileView 服务（可选）

如需使用文档预览功能，需要启动 KKFileView 服务：

```bash
# 使用 Docker 启动 KKFileView
docker-compose up -d
```

KKFileView 服务将在 http://localhost:8012 运行。

## 启动应用

```bash
streamlit run app.py
```

应用将在浏览器中打开，默认地址：http://localhost:8501

## 使用流程

### 1. 配置 LLM
- 在 "LLM 配置" 区域设置 Ollama 服务地址和模型
- 点击 "测试连接" 验证配置
- 点击 "应用配置" 保存设置

### 2. 创建和管理知识库
- 点击 "管理知识库" 进入知识库管理页面
- 点击 "新建知识库" 创建新的知识库
- 配置分块大小、重叠大小、召回数量、重排数量
- 点击 "使用此知识库" 切换到该知识库
- 在主页面上传文档到当前知识库

### 3. 上传文档
- 在侧边栏选择或创建知识库
- 上传需要建立知识库的文档
- 点击 "处理文档" 等待向量化完成

### 4. 开始问答
- 配置推理选项：启用知识库搜索、启用联网搜索、显示思考过程
- 在输入框中输入问题
- 系统会根据配置进行回答
- 可以查看回答的参考来源、点赞/点踩回答、复制回答

## 配置说明

在 `src/config/settings.py` 中可以修改以下配置，也可以通过环境变量设置：

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `OLLAMA_BASE_URL` | `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `OLLAMA_MODEL` | `qwen3.6:35b-a3b-q8_0` | 大模型名称 |
| `EMBEDDING_MODEL_NAME` | `EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | 嵌入模型名称 |
| `RERANK_MODEL_NAME` | `RERANK_MODEL_NAME` | `BAAI/bge-reranker-v2-m3` | 重排模型名称 |
| `CHUNK_SIZE` | `CHUNK_SIZE` | `500` | 文档分块大小（字符） |
| `CHUNK_OVERLAP` | `CHUNK_OVERLAP` | `50` | 分块重叠大小（字符） |
| `RECALL_TOP_K` | `RECALL_TOP_K` | `20` | 召回阶段返回的文档数量 |
| `RERANK_TOP_K` | `RERANK_TOP_K` | `5` | 重排后返回的文档数量 |
| `UPLOAD_DIR` | `UPLOAD_DIR` | `./uploads` | 文档上传目录 |
| `VECTOR_STORE_DIR` | `VECTOR_STORE_DIR` | `./vector_store` | 向量存储目录 |
| `SESSIONS_DIR` | `SESSIONS_DIR` | `./sessions` | 会话存储目录 |
| `KNOWLEDGE_BASES_DIR` | `KNOWLEDGE_BASES_DIR` | `./knowledge_bases` | 知识库存储目录 |

## Streamlit 配置

在 `.streamlit/config.toml` 中可以配置服务端口等参数：

```toml
[server]
port = 8501
address = "0.0.0.0"
maxUploadSize = 200

[browser]
serverAddress = "localhost"
serverPort = 8501
```

## 项目结构

```
mini_assistant/
├── app.py                            # Streamlit 主应用
├── requirements.txt                  # 依赖列表
├── README.md                         # 项目文档
├── app.log                           # 应用日志
├── docker-compose.yml                # KKFileView Docker 配置
├── .streamlit/
│   └── config.toml                   # Streamlit 配置（端口、上传大小等）
└── src/
    ├── __init__.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py               # 应用配置文件
    ├── core/
    │   ├── __init__.py
    │   ├── kb_manager.py             # 知识库管理器
    │   └── rag_engine.py             # RAG 引擎整合
    ├── data/
    │   ├── __init__.py
    │   ├── document_processor.py     # 文档处理模块
    │   └── vector_store.py           # FAISS 向量存储
    ├── models/
    │   ├── __init__.py
    │   ├── embeddings.py             # BGE-M3 嵌入和重排模型
    │   ├── retriever.py              # 检索器（Recall + Rerank）
    │   └── llm.py                    # Ollama LLM 客户端
    ├── services/
    │   ├── __init__.py
    │   ├── search.py                 # 网络搜索服务
    │   └── kkfileview_service.py     # KKFileView 文件预览服务
    └── utils/
        ├── __init__.py
        ├── file_utils.py             # 文件工具
        └── session_manager.py        # 会话管理
```

## RAG 流程说明

1. **文档处理**: 将上传的文档解析为文本，并按设定大小分块
2. **向量化**: 使用 BGE-M3 将文本块转为向量
3. **存储**: 使用 FAISS 建立向量索引并持久化
4. **Recall**: 根据用户问题，从向量库中召回最相关的文档块
5. **ReRank**: 使用 BGE-Reranker-v2-m3 对召回结果进行重排
6. **联网搜索**（可选）: 从互联网获取实时信息
7. **生成**: 将相关文档和搜索结果作为上下文，调用 LLM 生成回答

## 模型说明

### 嵌入模型: BAAI/bge-m3
- 支持文本、图像、语音多模态嵌入
- 性能优异，在多种检索任务上表现出色
- 支持多种语言

### 重排模型: BAAI/bge-reranker-v2-m3
- 专门优化的重排模型
- 提升检索精度，过滤噪声
- 支持长文本处理

## 注意事项

- 确保 Ollama 服务正在运行
- 首次运行会下载 BGE-M3 和 BGE-Reranker 模型（国内通过 hf-mirror 加速）
- 每个知识库独立存储文档和向量索引
- 支持多文件同时上传（最大 200MB）
- 会话数据自动保存在 `sessions` 目录
- 默认服务端口为 8501
