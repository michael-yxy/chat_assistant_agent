import streamlit as st
import config
import os
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

from search import WebSearch
from kb_manager import KBManager, KnowledgeBaseConfig

# 会话管理
SESSION_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
os.makedirs(SESSION_DIR, exist_ok=True)

def load_sessions():
    """加载所有会话列表"""
    sessions = []
    if os.path.exists(SESSION_DIR):
        for filename in os.listdir(SESSION_DIR):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                filepath = os.path.join(SESSION_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sessions.append({
                            'id': session_id,
                            'title': data.get('title', '未命名会话'),
                            'created_at': data.get('created_at', ''),
                            'updated_at': data.get('updated_at', '')
                        })
                except Exception as e:
                    print(f"Error loading session {session_id}: {e}")
    # 按更新时间排序
    sessions.sort(key=lambda x: x['updated_at'], reverse=True)
    return sessions

def load_session(session_id):
    """加载指定会话"""
    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
    return None

def save_session(session_id, chat_history, title=None):
    """保存会话"""
    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")
    session_data = {
        'title': title or chat_history[0]['content'][:16] + '...' if chat_history else '未命名会话',
        'chat_history': chat_history,
        'created_at': datetime.now().isoformat() if not os.path.exists(filepath) else load_session(session_id).get('created_at', datetime.now().isoformat()),
        'updated_at': datetime.now().isoformat()
    }
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving session {session_id}: {e}")

def delete_session(session_id):
    """删除会话"""
    filepath = os.path.join(SESSION_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

def generate_session_id():
    """生成会话ID"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def load_uploaded_files():
    """从文件中加载已上传的文件列表"""
    if config.UPLOADED_FILES_LIST.exists():
        try:
            with open(config.UPLOADED_FILES_LIST, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading uploaded files: {e}")
    return []

def save_uploaded_files(files_list):
    """保存已上传的文件列表到文件"""
    try:
        with open(config.UPLOADED_FILES_LIST, 'w', encoding='utf-8') as f:
            json.dump(files_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving uploaded files: {e}")

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


def render_kb_manager_page():
    st.title("🏛️ 知识库管理")
    
    if st.button("← 返回主页面", key="back_from_kb_manager"):
        st.session_state.page = 'main'
        st.rerun()
    
    st.markdown("---")
    
    # 初始化KB管理器
    if 'kb_manager' not in st.session_state:
        st.session_state.kb_manager = KBManager(Path(__file__).parent)
    
    kb_manager = st.session_state.kb_manager
    
    # 新建知识库表单
    with st.expander("➕ 新建知识库", expanded=False):
        st.markdown("#### 创建新的知识库")
        
        new_kb_name = st.text_input("知识库名称", placeholder="请输入知识库名称")
        new_kb_desc = st.text_area("知识库描述", placeholder="请输入知识库描述（可选）", height=60)
        
        st.markdown("**文档处理配置:**")
        col1, col2 = st.columns(2)
        with col1:
            new_chunk_size = st.number_input("片段大小", min_value=100, max_value=2000, value=500, step=50)
        with col2:
            new_chunk_overlap = st.number_input("重叠大小", min_value=0, max_value=200, value=50, step=10)
        
        st.markdown("**检索配置:**")
        col3, col4 = st.columns(2)
        with col3:
            new_recall_k = st.number_input("召回数量", min_value=1, max_value=50, value=20)
        with col4:
            new_rerank_k = st.number_input("重排数量", min_value=1, max_value=20, value=5)
        
        if st.button("✨ 创建知识库", use_container_width=True):
            if not new_kb_name.strip():
                st.error("请输入知识库名称")
            else:
                config = KnowledgeBaseConfig(
                    name=new_kb_name.strip(),
                    description=new_kb_desc.strip(),
                    chunk_size=new_chunk_size,
                    chunk_overlap=new_chunk_overlap,
                    recall_top_k=new_recall_k,
                    rerank_top_k=new_rerank_k
                )
                success = kb_manager.create_kb(config)
                if success:
                    st.success(f"✅ 知识库 '{new_kb_name}' 创建成功！")
                    st.rerun()
                else:
                    st.error(f"❌ 知识库 '{new_kb_name}' 已存在")
    
    st.markdown("---")
    
    # 知识库列表
    st.markdown("#### 📋 知识库列表")
    kbs = kb_manager.list_kbs()
    
    if not kbs:
        st.info("暂无知识库，请创建一个新的知识库")
        return
    
    for kb in kbs:
        stats = kb_manager.get_kb_stats(kb.name)
        is_active = st.session_state.get('current_kb') == kb.name
        
        with st.container():
            col_header = st.columns([3, 1, 1])
            with col_header[0]:
                st.markdown(f"**📁 {kb.name}**")
                if kb.description:
                    st.markdown(f"<small style='color: #666'>{kb.description}</small>", unsafe_allow_html=True)
            
            with col_header[1]:
                if st.button("⚙️ 配置", key=f"config_{kb.name}", use_container_width=True):
                    st.session_state.editing_kb = kb.name
                    st.rerun()
            
            with col_header[2]:
                if kb.name != "默认知识库":
                    if st.button("🗑️ 删除", key=f"delete_kb_{kb.name}", use_container_width=True):
                        st.session_state.deleting_kb = kb.name
            
            # 统计信息
            col_stats = st.columns(3)
            with col_stats[0]:
                st.metric("文档数", stats['documents'])
            with col_stats[1]:
                st.metric("片段数", stats['chunks'])
            with col_stats[2]:
                if st.button("🎯 使用此知识库", key=f"use_{kb.name}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.current_kb = kb.name
                    # 更新RAG引擎使用的向量存储路径
                    from rag_engine import RAGEngine
                    vector_store_path = kb_manager.get_kb_vector_store_path(kb.name)
                    st.session_state.rag_engine = RAGEngine(vector_store_path=vector_store_path)
                    # 清除缓存的统计信息和上传文件列表
                    if 'kb_stats' in st.session_state:
                        del st.session_state.kb_stats
                    if 'last_kb' in st.session_state:
                        del st.session_state.last_kb
                    st.success(f"✅ 已切换到知识库 '{kb.name}'")
                    st.rerun()
            
            # 删除确认
            if st.session_state.get('deleting_kb') == kb.name:
                st.warning(f"⚠️ 确定要删除知识库 '{kb.name}' 吗？此操作将删除所有文档和配置，不可恢复！")
                col_confirm = st.columns(2)
                with col_confirm[0]:
                    if st.button("✅ 确认删除", key=f"confirm_delete_kb_{kb.name}"):
                        success = kb_manager.delete_kb(kb.name)
                        if success:
                            st.success(f"✅ 知识库 '{kb.name}' 已删除")
                            if st.session_state.get('current_kb') == kb.name:
                                st.session_state.current_kb = "默认知识库"
                            st.session_state.deleting_kb = None
                            st.rerun()
                        else:
                            st.error("删除失败")
                with col_confirm[1]:
                    if st.button("❌ 取消", key=f"cancel_delete_kb_{kb.name}"):
                        st.session_state.deleting_kb = None
                        st.rerun()
            
            # 配置编辑
            if st.session_state.get('editing_kb') == kb.name:
                st.markdown("---")
                st.markdown(f"#### ⚙️ 编辑知识库: {kb.name}")
                
                new_desc = st.text_area("描述", value=kb.description, height=60, key=f"desc_{kb.name}")
                col_edit = st.columns(2)
                with col_edit[0]:
                    edit_chunk_size = st.number_input("片段大小", min_value=100, max_value=2000, value=kb.chunk_size, step=50, key=f"chunk_size_{kb.name}")
                with col_edit[1]:
                    edit_chunk_overlap = st.number_input("重叠大小", min_value=0, max_value=200, value=kb.chunk_overlap, step=10, key=f"chunk_overlap_{kb.name}")
                
                col_edit2 = st.columns(2)
                with col_edit2[0]:
                    edit_recall_k = st.number_input("召回数量", min_value=1, max_value=50, value=kb.recall_top_k, key=f"recall_k_{kb.name}")
                with col_edit2[1]:
                    edit_rerank_k = st.number_input("重排数量", min_value=1, max_value=20, value=kb.rerank_top_k, key=f"rerank_k_{kb.name}")
                
                col_buttons = st.columns(2)
                with col_buttons[0]:
                    if st.button("💾 保存配置", key=f"save_config_{kb.name}", use_container_width=True):
                        updated_config = KnowledgeBaseConfig(
                            name=kb.name,
                            description=new_desc,
                            chunk_size=edit_chunk_size,
                            chunk_overlap=edit_chunk_overlap,
                            recall_top_k=edit_recall_k,
                            rerank_top_k=edit_rerank_k
                        )
                        success = kb_manager.update_kb(kb.name, updated_config)
                        if success:
                            st.success("✅ 配置已保存")
                            st.session_state.editing_kb = None
                            st.rerun()
                        else:
                            st.error("保存失败")
                with col_buttons[1]:
                    if st.button("❌ 取消", key=f"cancel_edit_{kb.name}", use_container_width=True):
                        st.session_state.editing_kb = None
                        st.rerun()
            
            st.markdown("---")


def get_current_kb_paths():
    """获取当前知识库的路径配置"""
    current_kb = st.session_state.get('current_kb', '默认知识库')
    
    if 'kb_manager' in st.session_state:
        kb_manager = st.session_state.kb_manager
        upload_path = kb_manager.get_kb_upload_path(current_kb)
        vector_store_path = kb_manager.get_kb_vector_store_path(current_kb)
        uploaded_files_path = upload_path.parent / "uploaded_files.json"
    else:
        upload_path = config.UPLOAD_DIR
        vector_store_path = config.VECTOR_STORE_DIR
        uploaded_files_path = config.UPLOADED_FILES_LIST
    
    return upload_path, vector_store_path, uploaded_files_path

def load_kb_uploaded_files(uploaded_files_path):
    """从文件中加载已上传的文件列表"""
    if uploaded_files_path.exists():
        try:
            with open(uploaded_files_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading uploaded files: {e}")
    return []

def save_kb_uploaded_files(uploaded_files_path, files_list):
    """保存已上传文件列表到文件"""
    try:
        with open(uploaded_files_path, 'w', encoding='utf-8') as f:
            json.dump(files_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving uploaded files: {e}")

def render_knowledge_base_section():
    st.markdown("### 📚 知识库管理")
    
    # 知识库管理入口
    if st.button("🏛️ 管理知识库", use_container_width=True, type="secondary"):
        st.session_state.page = 'kb_manager'
        st.rerun()
    
    # 当前知识库信息
    current_kb = st.session_state.get('current_kb', '默认知识库')
    st.markdown(f"<small style='color: #666'>当前知识库: <strong>{current_kb}</strong></small>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 获取当前知识库的路径
    upload_path, vector_store_path, uploaded_files_path = get_current_kb_paths()
    
    # 加载当前知识库的已上传文件列表
    if 'uploaded_files' not in st.session_state or st.session_state.get('last_kb') != current_kb:
        st.session_state.uploaded_files = load_kb_uploaded_files(uploaded_files_path)
        st.session_state.last_kb = current_kb
    
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
                    # 确保上传目录存在
                    upload_path.mkdir(parents=True, exist_ok=True)
                    
                    saved_files = []
                    duplicate_files = []
                    new_files = []
                    
                    for uploaded_file in uploaded_files:
                        # 检查文件名是否重复
                        if uploaded_file.name in st.session_state.uploaded_files:
                            duplicate_files.append(uploaded_file.name)
                        else:
                            save_path = upload_path / uploaded_file.name
                            with open(save_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())
                            saved_files.append(save_path)
                            new_files.append(uploaded_file.name)
                    
                    # 显示重复文件警告
                    if duplicate_files:
                        st.warning(f"⚠️ 以下文件已存在，已跳过：{', '.join(duplicate_files)}")
                    
                    # 如果没有新文件，提示用户
                    if not saved_files:
                        st.info("💡 所有选择的文件都已存在，请选择其他文件上传")
                        return
                    
                    # 处理新文件
                    result = st.session_state.rag_engine.add_documents(saved_files)

                    st.session_state.uploaded_files.extend(new_files)
                    # 保存已上传文件列表
                    save_kb_uploaded_files(uploaded_files_path, st.session_state.uploaded_files)

                    st.success(f"""
                    ✅ 文档处理完成！
                    - 成功处理: {len(result['successful_files'])} 个文件
                    - 生成片段: {result['total_chunks']} 个
                    """)
                    if result['failed_files']:
                        st.warning(f"失败文件: {', '.join(result['failed_files'])}")
                    
                    # 清除缓存的统计信息并刷新页面
                    if 'kb_stats' in st.session_state:
                        del st.session_state.kb_stats
                    st.rerun()

                except Exception as e:
                    st.error(f"处理文档时出错: {str(e)}")
    
    # 已上传文件管理
    if st.session_state.get('uploaded_files'):
        with st.expander(f"📁 已上传文件 ({len(st.session_state.uploaded_files)})", expanded=False):
            # 初始化删除状态
            if 'file_to_delete' not in st.session_state:
                st.session_state.file_to_delete = None
            
            # 计算动态高度（每行文件约35px）
            file_count = len(st.session_state.uploaded_files)
            display_files = st.session_state.uploaded_files[-10:]  # 只显示最后10个
            dynamic_height = min(len(display_files) * 35 + 20, 200)  # 最多200px，最少显示所有文件
            
            # 创建可滚动容器
            st.markdown(f"""
            <style>
            .file-list-container {{
                max-height: {dynamic_height}px;
                overflow-y: auto;
            }}
            </style>
            """, unsafe_allow_html=True)
            
            # 显示要删除的文件确认对话框
            if st.session_state.file_to_delete:
                st.warning(f"⚠️ 确定要彻底删除文件 '{st.session_state.file_to_delete}' 吗？此操作不可恢复！")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 确认删除", key="confirm_delete"):
                        try:
                            # 删除物理文件（使用当前知识库路径）
                            file_path = upload_path / st.session_state.file_to_delete
                            if file_path.exists():
                                file_path.unlink()
                            
                            # 从已上传文件列表中删除
                            st.session_state.uploaded_files.remove(st.session_state.file_to_delete)
                            
                            # 重新构建向量索引（排除已删除的文件）
                            st.session_state.rag_engine.rebuild_index(
                                [upload_path / f for f in st.session_state.uploaded_files 
                                 if (upload_path / f).exists()]
                            )
                            
                            # 保存更新后的文件列表（使用当前知识库路径）
                            save_kb_uploaded_files(uploaded_files_path, st.session_state.uploaded_files)
                            
                            # 清除缓存的统计信息
                            if 'kb_stats' in st.session_state:
                                del st.session_state.kb_stats
                            
                            st.success(f"✅ 文件 '{st.session_state.file_to_delete}' 已彻底删除")
                            st.session_state.file_to_delete = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除文件时出错: {str(e)}")
                            st.session_state.file_to_delete = None
                
                with col2:
                    if st.button("❌ 取消", key="cancel_delete"):
                        st.session_state.file_to_delete = None
                        st.rerun()
            else:
                # 显示文件列表，使用容器实现滚动
                with st.container():
                    st.markdown('<div class="file-list-container">', unsafe_allow_html=True)
                    
                    for idx, filename in enumerate(display_files):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.text(f"📄 {filename}")
                        with col2:
                            if st.button("🗑️", key=f"delete_btn_{idx}_{len(st.session_state.uploaded_files)}", help=f"删除 {filename}"):
                                st.session_state.file_to_delete = filename
                                st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
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
    
    # 使用缓存来避免每次加载页面都触发VectorStore加载
    if 'kb_stats' not in st.session_state:
        st.session_state.kb_stats = st.session_state.rag_engine.get_stats()
    else:
        # 每30秒刷新一次统计
        if 'stats_last_update' not in st.session_state or \
           (time.time() - st.session_state.stats_last_update) > 30:
            st.session_state.kb_stats = st.session_state.rag_engine.get_stats()
            st.session_state.stats_last_update = time.time()
    
    stats = st.session_state.kb_stats
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("文档数", stats['total_documents'])
    
    with col2:
        st.metric("片段数", stats['index_size'])
    
    if stats['total_documents'] > 0 or stats['index_size'] > 0:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if stats['total_documents'] > 0:
                if st.button("📋 文档列表", key="doc-btn", use_container_width=True):
                    st.session_state.page = 'doc_preview'
                    st.rerun()
        
        with col_btn2:
            if stats['index_size'] > 0:
                if st.button("📋 片段列表", key="chunk-btn", use_container_width=True):
                    st.session_state.page = 'chunk_preview'
                    st.rerun()

    if stats['total_documents'] == 0:
        st.info("💡 当前知识库为空，系统将以对话模式运行")

    if st.button("🗑️ 清空知识库", use_container_width=True):
        try:
            # 删除uploads目录下的所有文件
            import shutil
            for file_path in config.UPLOAD_DIR.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            
            # 删除vector_store目录下的所有文件
            for file_path in config.VECTOR_STORE_DIR.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            
            # 重置RAG引擎
            st.session_state.rag_engine.reset()
            
            # 清空会话状态
            st.session_state.uploaded_files = []
            st.session_state.chat_history = []
            
            # 清空已上传文件列表
            save_uploaded_files([])
            
            # 清除缓存的统计信息
            if 'kb_stats' in st.session_state:
                del st.session_state.kb_stats
            
            st.success("✅ 知识库已彻底清空，所有文档和片段均已删除")
            
            # 刷新页面以显示最新统计
            st.rerun()
        except Exception as e:
            st.error(f"清空知识库时出错: {str(e)}")


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
                            source_type = source.get('type', 'knowledge')
                            
                            if source_type == 'web' and source.get('url'):
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>🌐 搜索结果 {idx}:</strong> <a href="{source['url']}" target="_blank">{source['source']}</a> ({score_type}: {score:.4f})<br>
                                    <em>{source['content']}</em>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div class="source-card">
                                    <strong>📄 来源 {idx}:</strong> {source['source']} ({score_type}: {score:.4f})<br>
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
        st.session_state.uploaded_files = load_uploaded_files()
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
    if 'use_web_search' not in st.session_state:
        st.session_state.use_web_search = True
    if 'use_knowledge_search' not in st.session_state:
        st.session_state.use_knowledge_search = True
    if 'search_results_count' not in st.session_state:
        st.session_state.search_results_count = 5
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'page' not in st.session_state:
        st.session_state.page = 'main'
    if 'rag_engine' not in st.session_state:
        from rag_engine import RAGEngine
        from config import VECTOR_STORE_DIR
        st.session_state.rag_engine = RAGEngine(vector_store_path=VECTOR_STORE_DIR)
        # 不在初始化时测试连接，只在用户点击测试时才测试
        st.session_state.last_test_result = None
        
        # 预热LLM客户端，避免第一次对话延迟
        def warm_up_llm():
            try:
                import threading
                def do_warmup():
                    try:
                        # 发送一个简单的请求来触发Ollama模型加载
                        llm_client = st.session_state.rag_engine.llm_client
                        # 发送一个简单的测试请求来预热模型
                        for chunk in llm_client.chat_stream("hello"):
                            if chunk.get("done"):
                                break
                    except Exception as e:
                        pass
                threading.Thread(target=do_warmup, daemon=True).start()
            except:
                pass

    # 初始化会话状态
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = generate_session_id()
    
    # 加载会话列表
    sessions = load_sessions()
    
    # 知识库管理页面
    if st.session_state.page == 'kb_manager':
        render_kb_manager_page()
        return
    
    # 文档预览页面
    if st.session_state.page == 'doc_preview':
        st.title("📋 文档列表预览")
        if st.button("← 返回主页面", key="back_from_doc"):
            st.session_state.page = 'main'
            st.rerun()
        
        st.markdown("---")
        documents = st.session_state.rag_engine.vector_store.get_all_documents()
        st.markdown(f"### 共 {len(documents)} 个文档")
        
        for doc_name in documents:
            st.markdown(f"#### 📄 {doc_name}")
            chunks = st.session_state.rag_engine.vector_store.get_chunks_by_document(doc_name)
            if chunks:
                st.markdown(f"**包含 {len(chunks)} 个片段:**")
                for i, chunk in enumerate(chunks, 1):
                    with st.expander(f"片段 {i}", expanded=False):
                        st.markdown(f"{chunk['content']}")
            st.markdown("---")
        return
    
    # 片段预览页面
    if st.session_state.page == 'chunk_preview':
        st.title("📑 片段列表预览")
        if st.button("← 返回主页面", key="back_from_chunk"):
            st.session_state.page = 'main'
            st.rerun()
        
        st.markdown("---")
        chunks = st.session_state.rag_engine.vector_store.get_all_chunks()
        st.markdown(f"### 共 {len(chunks)} 个片段")
        
        for i, chunk in enumerate(chunks, 1):
            st.markdown(f"#### 片段 {i}")
            st.markdown(f"**来源:** {chunk['metadata'].get('source', '未知')}")
            st.markdown(f"**内容:**")
            st.markdown(chunk['content'])
            st.markdown("---")
        return
    
    # 初始化折叠状态
    if 'sidebar_collapsed' not in st.session_state:
        st.session_state.sidebar_collapsed = False
    
    # 根据折叠状态计算主内容占比，用于设置输入框宽度
    if st.session_state.sidebar_collapsed:
        # 折叠状态：主内容占 3/4，输入框靠左
        main_content_ratio = 0.75
        input_align_left = True
    else:
        # 展开状态：主内容占 3/5，输入框居中
        main_content_ratio = 0.6
        input_align_left = False
    
    # 添加自定义 CSS 控制输入框宽度和对齐
    if input_align_left:
        # 折叠时靠左对齐，与主内容列位置匹配
        st.markdown(f"""
        <style>
        .stChatInput {{
            max-width: {main_content_ratio * 100}% !important;
            margin-right: auto !important;
            margin-left: 0 !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        # 展开时居中对齐
        st.markdown(f"""
        <style>
        .stChatInput {{
            max-width: {main_content_ratio * 100}% !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # 根据折叠状态调整布局
    if st.session_state.sidebar_collapsed:
        # 折叠状态：两列布局（主内容 + 知识库管理）
        col_main, col_kb = st.columns([3, 1])
        
        with col_kb:
            # 右侧：知识库管理
            render_knowledge_base_section()
        
        with col_main:
            # 展开按钮放在主区域顶部
            if st.button("📋 展开会话历史", use_container_width=False):
                st.session_state.sidebar_collapsed = False
                st.rerun()
            
            # 主区域：LLM配置 + 聊天
            st.title("🤖 智能问答助手")
            st.markdown("基于RAG技术的智能问答系统，支持文档上传和知识库检索")
            
            # LLM配置
            render_llm_config_section()
            
            st.markdown("---")
            
            # 搜索配置
            st.markdown("### 🔍 搜索选项")
            col_search1, col_search2 = st.columns([1, 1])
            with col_search1:
                use_knowledge_search = st.toggle("📚 知识库搜索", value=st.session_state.use_knowledge_search, key="knowledge_search_toggle")
                st.session_state.use_knowledge_search = use_knowledge_search
            with col_search2:
                use_web_search = st.toggle("🌐 联网搜索", value=st.session_state.use_web_search, key="web_search_toggle")
                st.session_state.use_web_search = use_web_search
            
            st.markdown("💡 提示：启用知识库搜索将从上传的文档中检索相关信息，启用联网搜索将从互联网获取实时信息。")
            
            st.markdown("---")
            
            # 聊天界面
            st.markdown("### 💬 对话")
            render_chat_interface()
    else:
        # 展开状态：三列布局（会话列表 + 主内容 + 知识库管理）
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            # 左侧：会话历史列表
            # 折叠按钮
            col_title, col_collapse = st.columns([4, 1])
            with col_title:
                st.markdown("### 📋 会话历史")
            with col_collapse:
                if st.button("«", key="collapse_sidebar", help="隐藏会话历史"):
                    st.session_state.sidebar_collapsed = True
                    st.rerun()
            
            # 新建会话按钮
            if st.button("➕ 新建会话", use_container_width=True):
                st.session_state.current_session_id = generate_session_id()
                st.session_state.chat_history = []
                st.rerun()
            
            st.markdown("---")
            
            # 会话列表
            for session in sessions:
                is_active = session['id'] == st.session_state.current_session_id
                col_btn, col_del = st.columns([5, 1])
                with col_btn:
                    if st.button(
                        session['title'],
                        key=f"session_{session['id']}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"
                    ):
                        st.session_state.current_session_id = session['id']
                        session_data = load_session(session['id'])
                        if session_data:
                            st.session_state.chat_history = session_data.get('chat_history', [])
                        st.rerun()
                with col_del:
                    if st.button("x", key=f"del_{session['id']}", use_container_width=True):
                        delete_session(session['id'])
                        if session['id'] == st.session_state.current_session_id:
                            st.session_state.current_session_id = generate_session_id()
                            st.session_state.chat_history = []
                        st.rerun()
        
        with col3:
            # 右侧：知识库管理
            render_knowledge_base_section()
        
        with col2:
            # 主区域：LLM配置 + 聊天
            st.title("🤖 智能问答助手")
            st.markdown("基于RAG技术的智能问答系统，支持文档上传和知识库检索")
            
            # LLM配置
            render_llm_config_section()
            
            st.markdown("---")
            
            # 搜索配置
            st.markdown("### 🔍 搜索选项")
            col_search1, col_search2 = st.columns([1, 1])
            with col_search1:
                use_knowledge_search = st.toggle("📚 知识库搜索", value=st.session_state.use_knowledge_search, key="knowledge_search_toggle")
                st.session_state.use_knowledge_search = use_knowledge_search
            with col_search2:
                use_web_search = st.toggle("🌐 联网搜索", value=st.session_state.use_web_search, key="web_search_toggle")
                st.session_state.use_web_search = use_web_search
            
            st.markdown("💡 提示：启用知识库搜索将从上传的文档中检索相关信息，启用联网搜索将从互联网获取实时信息。")
            
            st.markdown("---")
            
            # 聊天界面
            st.markdown("### 💬 对话")
            render_chat_interface()
    
    # 用户输入固定在底部（两种状态共用）
    user_input = st.chat_input(
        "请输入您的问题，我会根据知识库为您解答",
        key="user_input"
    )
    
    # 用户输入处理（两种状态共用）
    if user_input:
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        full_response = ""
        thinking_content = ""
        current_mode = "chat"
        sources = []
        search_results = []
        
        with st.chat_message("assistant"):
            with st.expander("🧠 思考过程（实时）", expanded=True):
                think_placeholder = st.empty()
            
            answer_box = st.empty()
            
            think_buf = ""
            answer_buf = ""
            
            # 检查知识库状态（这应该很快，因为统计已经缓存）
            stats = st.session_state.rag_engine.vector_store.get_stats()
            has_knowledge_base = stats['total_documents'] > 0
            use_web_search = st.session_state.use_web_search
            use_knowledge_search = st.session_state.use_knowledge_search
            
            # 收集所有上下文（知识库 + 搜索结果）
            contexts = []
            retrieved_docs = None
            search_results = []
            use_rag = has_knowledge_base and use_knowledge_search
            
            result_queue = queue.Queue()
            
            def retrieve_docs():
                try:
                    retrieved_docs = st.session_state.rag_engine.retriever.retrieve(
                        query=user_input,
                        recall_top_k=st.session_state.recall_k,
                        rerank_top_k=st.session_state.rerank_k if st.session_state.use_rerank else st.session_state.recall_k
                    )
                    result_queue.put(('retrieve', retrieved_docs))
                except Exception as e:
                    result_queue.put(('retrieve_error', str(e)))
            
            def web_search():
                try:
                    searcher = WebSearch()
                    num_results = st.session_state.get('search_results_count', 5)
                    if num_results > 0:
                        results = searcher.search_with_content(user_input, num_results=num_results)
                        result_queue.put(('search', results))
                    else:
                        result_queue.put(('search', []))
                except Exception as e:
                    result_queue.put(('search_error', str(e)))
            
            # 优先进行知识库搜索
            if use_rag:
                think_buf = "🔍 正在检索知识库..."
                think_placeholder.markdown(think_buf)
                try:
                    retrieved_docs = st.session_state.rag_engine.retriever.retrieve(
                        query=user_input,
                        recall_top_k=st.session_state.recall_k,
                        rerank_top_k=st.session_state.rerank_k if st.session_state.use_rerank else st.session_state.recall_k
                    )
                    think_buf += f"\n✅ 知识库检索完成，获取到{len(retrieved_docs)}条相关文档"
                    think_placeholder.markdown(think_buf)
                    sources.extend([
                        {
                            'content': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                            'source': doc['metadata']['source'],
                            'score': doc.get('rerank_score', doc.get('distance', 0)),
                            'type': 'knowledge'
                        }
                        for doc in retrieved_docs
                    ])
                    contexts.extend([doc['content'] for doc in retrieved_docs])
                except Exception as e:
                    think_buf += f"\n⚠️ 知识库检索失败: {str(e)}"
                    think_placeholder.markdown(think_buf)
            
            # 知识库搜索完成后，再进行联网搜索
            if use_web_search:
                if think_buf:
                    think_buf += "\n"
                think_buf += "🌐 正在进行联网搜索..."
                think_placeholder.markdown(think_buf)
                try:
                    searcher = WebSearch()
                    num_results = st.session_state.get('search_results_count', 5)
                    if num_results > 0:
                        search_results = searcher.search_with_content(user_input, num_results=num_results)
                    else:
                        search_results = []
                    
                    think_buf += f"\n✅ 联网搜索完成，获取到{len(search_results)}条结果：\n"
                    for r in search_results:
                        think_buf += f"- [{r['title']}]({r['url']})\n"
                    think_placeholder.markdown(think_buf)
                    sources.extend([
                        {
                            'content': r['content'][:200] + "..." if len(r['content']) > 200 else r['content'],
                            'source': r['title'],
                            'url': r['url'],
                            'score': 1.0 - (r['rank'] * 0.1),
                            'type': 'web'
                        }
                        for r in search_results
                    ])
                    contexts.extend([f"【{r['title']}】\n{r['content']}" for r in search_results])
                except Exception as e:
                    think_buf += f"\n⚠️ 联网搜索失败: {str(e)}"
                    think_placeholder.markdown(think_buf)
            
            # 开始生成答案
            if think_buf:
                think_buf += "\n\n"
            think_buf += "🧠 正在分析并生成答案..."
            think_placeholder.markdown(think_buf)
            
            # 根据上下文生成答案
            if contexts:
                for chunk in st.session_state.rag_engine.llm_client.generate_with_context_stream(query=user_input, context=contexts):
                    if chunk.get("thinking"):
                        think_buf += chunk["thinking"]
                        think_placeholder.markdown(think_buf)
                    if chunk.get("content"):
                        answer_buf += chunk["content"]
                        answer_box.markdown(answer_buf)
            else:
                for chunk in st.session_state.rag_engine.llm_client.chat_stream(query=user_input):
                    if chunk.get("thinking"):
                        think_buf += chunk["thinking"]
                        think_placeholder.markdown(think_buf)
                    if chunk.get("content"):
                        answer_buf += chunk["content"]
                        answer_box.markdown(answer_buf)
        
        full_response = answer_buf
        
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': full_response,
            'thinking': think_buf,
            'mode': current_mode,
            'sources': sources,
            'search_results': search_results
        })
        
        # 保存会话
        save_session(st.session_state.current_session_id, st.session_state.chat_history)


if __name__ == '__main__':
    main()
