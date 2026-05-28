import httpx
from typing import Optional, List, Dict
import logging
import json

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3.6:35b-a3b-q8_0",
        api_key: str = "ollama"
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.client = httpx.Client(timeout=300.0)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {e}")
            return f"Error: Unable to connect to LLM service. Please check if Ollama is running."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"

    def generate_with_context(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None
    ) -> str:
        context_text = "\n\n".join([f"[Document {i+1}]:\n{doc}" for i, doc in enumerate(context)])

        if system_prompt is None:
            system_prompt = """You are a helpful AI assistant. You will be given a question and relevant context from documents. 

Your task:
1. Answer the question based ONLY on the provided context
2. If the context doesn't contain enough information to fully answer the question, clearly state what information is available
3. Be precise and cite which document(s) support your answer when possible
4. If you cannot find relevant information in the context, say so

IMPORTANT: Do not make up information that is not present in the context.

你是一名实用的人工智能助手。你将收到一个问题以及来自文档的相关上下文信息。
你的任务：
仅依据所提供的上下文回答问题
若上下文信息不足以完整回答问题，需清晰说明现有可用信息
回答需精准，尽可能标注支撑答案的文档来源
若在上下文中未找到相关信息，直接说明即可
重要要求：不得编造上下文中不存在的信息。

使用中文输出思考过程。
"""

        prompt = f"""Context:
{context_text}

Question: {query}

Please provide a helpful answer based on the context above."""

        return self.generate(prompt, system_prompt=system_prompt)

    def chat(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ) -> str:
        if system_prompt is None:
            system_prompt = """你是一个帮助用户解答问题的AI助手。

思考过程格式要求：
1. 在回答之前，先输出你的思考过程
2. 思考过程用【深度思考】标签包裹
3. 思考过程要详细，包括：分析问题、搜索相关知识、整理思路等
4. 思考完成后再给出最终回答

输出格式示例：
【深度思考】
用户问的是...
我需要分析...
我已经获得了...
现在可以组织回答...
【/深度思考】

最终回答：
(你的详细回答内容)
"""

        return self.generate(query, system_prompt=system_prompt)
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        think: bool = True
    ):
        """流式生成回答 - 使用 Ollama /api/chat API，支持实时思考过程"""
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        # 使用 Ollama /api/chat API
        base_url_no_v1 = self.base_url.replace("/v1", "")
        api_url = f"{base_url_no_v1}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": think,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        logger.info(f"Starting stream request to {api_url}")
        
        try:
            with httpx.stream(
                "POST",
                api_url,
                json=payload,
                timeout=120.0,
                follow_redirects=True
            ) as response:
                response.raise_for_status()
                logger.info("Connected to streaming API, waiting for chunks...")
                
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    try:
                        chunk = json.loads(line)
                        msg = chunk.get("message") or {}
                        
                        yield {
                            "content": msg.get("content", ""),
                            "thinking": msg.get("thinking", ""),
                            "done": chunk.get("done", False)
                        }
                        
                        if chunk.get("done"):
                            logger.info("Received done, stream completed")
                            return
                            
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode error: {e}")
                        continue
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {e}")
            yield {"content": f"Error: Unable to connect to LLM service. Please check if Ollama is running.", "thinking": "", "done": True}
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            yield {"content": f"Error: {str(e)}", "thinking": "", "done": True}
    
    def chat_stream(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ):
        """流式聊天 - 使用 Ollama /api/chat API"""
        if system_prompt is None:
            system_prompt = """你是一个有深度思考能力的AI助手。请根据用户的问题给出准确、详细的回答。"""

        return self.generate_stream(query, system_prompt=system_prompt, think=True)
    
    def generate_with_context_stream(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None
    ):
        """流式生成带上下文的回答 - 使用 Ollama /api/chat API"""
        context_text = "\n\n".join([f"[Document {i+1}]:\n{doc}" for i, doc in enumerate(context)])

        if system_prompt is None:
            system_prompt = """你是一个有深度思考能力的AI助手。请根据提供的上下文信息，回答用户的问题。如果上下文不足以回答问题，请明确说明。"""

        prompt = f"""Context:
{context_text}

Question: {query}

Please provide a helpful answer based on the context above."""

        return self.generate_stream(prompt, system_prompt=system_prompt)

    def test_connection(self, model_name: Optional[str] = None) -> Dict:
        """测试与LLM服务的连接，可指定模型名称"""
        target_model = model_name if model_name else self.model
        
        try:
            base_url_no_v1 = self.base_url.replace("/v1", "")
            
            # 第一步：获取模型列表验证服务是否运行
            model_list_response = self.client.get(
                f"{base_url_no_v1}/api/tags",
                timeout=5.0
            )
            
            if model_list_response.status_code != 200:
                return {
                    "success": False,
                    "message": f"❌ 无法获取模型列表 (状态码: {model_list_response.status_code})",
                    "status": "service_error"
                }
            
            model_data = model_list_response.json()
            available_models = [m.get("name", "") for m in model_data.get("models", [])]
            
            # 检查模型是否在列表中
            if target_model not in available_models:
                return {
                    "success": False,
                    "message": f"❌ 模型 '{target_model}' 未找到。可用模型: {', '.join(available_models) if available_models else '无'}",
                    "status": "model_not_found"
                }
            
            # 第二步：真正发送请求测试模型是否能正常响应
            test_payload = {
                "model": target_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            test_response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=test_payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if test_response.status_code == 200:
                result = test_response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return {
                        "success": True,
                        "message": f"✅ 连接成功！模型 '{target_model}' 响应正常",
                        "status": "connected"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ 模型 '{target_model}' 响应格式异常",
                        "status": "response_format_error"
                    }
            else:
                try:
                    error_data = test_response.json()
                    error_msg = error_data.get("error", {}).get("message", f"状态码: {test_response.status_code}")
                except:
                    error_msg = f"状态码: {test_response.status_code}"
                
                return {
                    "success": False,
                    "message": f"❌ 模型 '{target_model}' 响应异常: {error_msg}",
                    "status": "model_error"
                }
                    
        except httpx.ConnectError:
            return {
                "success": False,
                "message": "❌ 无法连接到服务，请确认服务地址正确且Ollama正在运行",
                "status": "connection_refused"
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "❌ 连接超时，模型可能正在加载或服务异常",
                "status": "timeout"
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "message": f"❌ 连接测试失败: {str(e)}",
                "status": "error"
            }

    def get_available_models(self) -> List[str]:
        """获取Ollama中可用的模型列表"""
        try:
            base_url_no_v1 = self.base_url.replace("/v1", "")
            response = self.client.get(
                f"{base_url_no_v1}/api/tags",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                models = []
                if "models" in data:
                    for model in data["models"]:
                        models.append(model.get("name", ""))
                return models
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Failed to get model list: {e}")
            return []

    def close(self):
        self.client.close()


def create_llm_client(
    base_url: str = "http://localhost:11434/v1",
    model: str = "qwen3.6:35b-a3b-q8_0",
    api_key: str = "ollama"
) -> LLMClient:
    return LLMClient(base_url=base_url, model=model, api_key=api_key)