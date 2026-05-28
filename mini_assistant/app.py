import streamlit as st
import config
import os

os.environ["STREAMLIT_SERVER_PORT"] = "8501"
def render_llm_config_section():
    st.markdown("### 🔧 LLM 配置")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        new_base_url = st.text_input(
            "服务地址",
            value=st.session_state.get('llm_base_url', config.OLLAMA_BASE_URL),
            help="大模型API服务地址"
        )
    
    with col2:
        try:
            available_models = st.session_state.rag_engine.get_available_models()
            current_model = st.session_state.get('llm_model', config.OLLAMA_MODEL)
            
            if current_model not in available_models:
                available_models.insert(0, current_model)
            
            new_model = st.selectbox(
                "选择模型",
                options=available_models if available_models else [current_model],
                index=available_models.index(current_model) if (available_models and current_model in available_models) else 0,
                help="从Ollama获取的可用模型列表"
            )
        except Exception as e:
            new_model = st.text_input(
                "模型名称",
                value=st.session_state.get('llm_model', config.OLLAMA_MODEL)
            )
    
    st.markdown("---")
    col_info, col_status = st.columns([3, 1])
    with col_info:
        st.markdown(f"""
        <div style="font-size: 0.9rem;">
        <strong>已应用配置：</strong>
        <br>服务地址: <code>{st.session_state.get('llm_base_url', config.OLLAMA_BASE_URL)}</code>
        <br>模型名称: <code>{st.session_state.get('llm_model', config.OLLAMA_MODEL)}</code>
        </div>
        """, unsafe_allow_html=True)
    
    with col_status:
        if st.session_state.last_test_result:
            if st.session_state.last_test_result["success"]:
                st.success("✓ 已连接")
            else:
                st.error("✗ 未连接")
    
    if st.session_state.last_test_result:
        if st.session_state.last_test_result["success"]:
            st.success(st.session_state.last_test_result["message"])
        else:
            st.error(st.session_state.last_test_result["message"])
    
    col1, col2 = st.columns([1, 1])
    with col1:
        test_button = st.button("🔌 测试连接", use_container_width=True)
        if test_button:
            with st.spinner("测试中..."):
                result = st.session_state.rag_engine.test_model_connection(model_name=new_model)
                st.session_state.last_test_result = result
                st.rerun()
    
    with col2:
        apply_button = st.button("💾 应用配置", use_container_width=True)
        if apply_button:
            with st.spinner("应用中..."):
                result = st.session_state.rag_engine.update_llm_config(
                    base_url=new_base_url,
                    model=new_model
                )
                st.session_state.last_test_result = result
                if result["success"]:
                    st.session_state.llm_base_url = new_base_url
                    st.session_state.llm_model = new_model
                st.rerun()


def render_knowledge_base_section():
    st.markdown("### 📚 知识库管理")
    
    uploaded_files = st.file_uploader(
        "上传文档",
        type=['pdf', 'docx', 'txt', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help="支持 PDF、DOCX、TXT、Excel 格式"
    )
    
    if uploaded_files:
        if st.button("✨ 处理文档", use_container_width=True):
            with st.spinner("正在处理文档..."):
                try:
                    saved_files = []
                    for uploaded_file in uploaded_files:
                        save_path = config.UPLOAD_DIR / uploaded_file.name
                        with open(save_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())
                        saved_files.append(save_path)

                    result = st.session_state.rag_engine.add_documents(saved_files)

                    st.session_state.uploaded_files.extend(
                        [f.name for f in saved_files]
                    )

                    st.success(f"""
                    ✅ 文档处理完成！
                    - 成功处理: {len(result['successful_files'])} 个文件
                    - 生成片段: {result['total_chunks']} 个
                    """)
                    if result['failed_files']:
                        st.warning(f"失败文件: {', '.join(result['failed_files'])}")

                except Exception as e:
                    st.error(f"处理文档时出错: {str(e)}")
    
    if st.session_state.get('uploaded_files'):
        with st.expander("📁 已上传文件", expanded=False):
            for filename in st.session_state.uploaded_files[-10:]:
                st.text(f"📄 {filename}")
    
    st.markdown("---")
    st.markdown("#### ⚙️ 检索设置")
    col1, col2 = st.columns([1, 1])
    with col1:
        recall_k = st.slider("召回数量", 5, 50, 20, help="Recall阶段返回的文档数量")
    with col2:
        rerank_k = st.slider("重排数量", 1, 10, 5, help="Rerank后返回的文档数量")
    
    use_rerank = st.checkbox("启用重排", value=True, help="是否启用Rerank阶段")
    
    st.session_state.recall_k = recall_k
    st.session_state.rerank_k = rerank_k
    st.session_state.use_rerank = use_rerank
    
    st.markdown("---")
    st.markdown("#### 📊 知识库统计")
    stats = st.session_state.rag_engine.get_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("文档数", stats['total_documents'])
    with col2:
        st.metric("片段数", stats['index_size'])

    if stats['total_documents'] == 0:
        st.info("💡 当前知识库为空，系统将以对话模式运行")

    if st.button("🗑️ 清空知识库", use_container_width=True):
        st.session_state.rag_engine.reset()
        st.session_state.uploaded_files = []
        st.session_state.chat_history = []
        st.success("知识库已清空")


def render_chat_interface():
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.markdown(message['content'])
        else:
            with st.chat_message("assistant"):
                thinking_content = message.get('thinking', '')
                answer_text = message.get('content', '')
                
                if thinking_content:
                    with st.expander("🧠 思考过程", expanded=False):
                        st.markdown(thinking_content)
                
                st.markdown(answer_text)
                
                if message.get('sources'):
                    with st.expander("📚 查看参考来源", expanded=False):
                        for idx, source in enumerate(message['sources'], 1):
                            score_type = "相关度" if 'rerank_score' in source else "相似度"
                            score = source.get('rerank_score', source.get('distance', 0))
                            st.markdown(f"""
                            <div class="source-card">
                                <strong>来源 {idx}:</strong> {source['source']} ({score_type}: {score:.4f})<br>
                                <em>{source['content']}</em>
                            </div>
                            """, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="智能问答助手",
        page_icon="🤖",
        layout="wide"
    )

    # 自定义样式
    st.markdown("""
    <style>
    .user-message {
        background-color: #e8f4fd;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 8px;
        max-width: 80%;
    }
    .assistant-message {
        background-color: #f5f5f5;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 8px;
        max-width: 80%;
    }
    .mode-rag {
        background-color: #667eea;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin-bottom: 4px;
        display: inline-block;
    }
    .mode-chat {
        background-color: #10b981;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin-bottom: 4px;
        display: inline-block;
    }
    .source-card {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .thinking-step {
        color: #666;
        font-style: italic;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # 初始化会话状态
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    if 'last_test_result' not in st.session_state:
        st.session_state.last_test_result = None
    if 'llm_base_url' not in st.session_state:
        st.session_state.llm_base_url = config.OLLAMA_BASE_URL
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = config.OLLAMA_MODEL
    if 'recall_k' not in st.session_state:
        st.session_state.recall_k = 20
    if 'rerank_k' not in st.session_state:
        st.session_state.rerank_k = 5
    if 'use_rerank' not in st.session_state:
        st.session_state.use_rerank = True
    if 'rag_engine' not in st.session_state:
        from rag_engine import RAGEngine
        st.session_state.rag_engine = RAGEngine()
        st.session_state.last_test_result = st.session_state.rag_engine.test_current_connection()

    # 主界面布局
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # 侧边栏：知识库管理
        render_knowledge_base_section()
    
    with col1:
        # 主区域：LLM配置 + 聊天
        st.title("🤖 智能问答助手")
        st.markdown("基于RAG技术的智能问答系统，支持文档上传和知识库检索")
        
        # LLM配置
        render_llm_config_section()
        
        st.markdown("---")
        
        # 聊天界面
        st.markdown("### 💬 对话")
        render_chat_interface()
        
        # 添加CSS固定输入框在底部，与上方按钮对齐
        st.markdown("""
        <style>
        div[data-testid="stChatInput"] {
            position: fixed;
            bottom: 1rem;
            left: 5rem;
            right: 32rem;
            width: auto;
            background: white;
            padding: 0.5rem 0;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
            z-index: 100;
        }
        </style>
        """, unsafe_allow_html=True)
        
        user_input = st.chat_input(
            "请输入您的问题，我会根据知识库为您解答",
            key="user_input"
        )
        
        if user_input:
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_input
            })
            
            full_response = ""
            thinking_content = ""
            current_mode = "chat"
            sources = []
            
            with st.chat_message("assistant"):
                with st.expander("🧠 思考过程（实时）", expanded=True):
                    think_placeholder = st.empty()
                
                answer_box = st.empty()
                
                think_buf = ""
                answer_buf = ""
                
                stats = st.session_state.rag_engine.vector_store.get_stats()
                has_knowledge_base = stats['total_documents'] > 0
                
                if has_knowledge_base:
                    retrieved_docs = st.session_state.rag_engine.retriever.retrieve(
                        query=user_input,
                        recall_top_k=st.session_state.recall_k,
                        rerank_top_k=st.session_state.rerank_k if st.session_state.use_rerank else st.session_state.recall_k
                    )
                    
                    if retrieved_docs:
                        current_mode = 'rag'
                        sources = [
                            {
                                'content': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                                'source': doc['metadata']['source'],
                                'score': doc.get('rerank_score', doc.get('distance', 0))
                            }
                            for doc in retrieved_docs
                        ]
                        contexts = [doc['content'] for doc in retrieved_docs]
                        
                        for chunk in st.session_state.rag_engine.llm_client.generate_with_context_stream(
                            query=user_input,
                            context=contexts
                        ):
                            if chunk.get("thinking"):
                                think_buf += chunk["thinking"]
                                think_placeholder.markdown(think_buf)
                            if chunk.get("content"):
                                answer_buf += chunk["content"]
                                answer_box.markdown(answer_buf)
                            
                            if chunk.get("done"):
                                break
                else:
                    current_mode = 'chat'
                    for chunk in st.session_state.rag_engine.llm_client.chat_stream(query=user_input):
                        if chunk.get("thinking"):
                            think_buf += chunk["thinking"]
                            think_placeholder.markdown(think_buf)
                        if chunk.get("content"):
                            answer_buf += chunk["content"]
                            answer_box.markdown(answer_buf)
                            
                        if chunk.get("done"):
                            break
            
            full_response = answer_buf
            
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': full_response,
                'thinking': think_buf,
                'mode': current_mode,
                'sources': sources
            })


if __name__ == '__main__':
    main()