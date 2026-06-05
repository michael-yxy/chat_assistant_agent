import requests
import base64

KKFILEVIEW_URL = "http://localhost:8012"

def is_kkfileview_available():
    try:
        response = requests.get(f"{KKFILEVIEW_URL}/index", timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_file_preview_url(file_path):
    container_path = file_path.replace(
        "/Users/george/Documents/开发/develop/mini_assistant/knowledge_bases",
        "/opt/kkfileview/knowledge_bases"
    )
    file_url = f"file://{container_path}"
    encoded_url = base64.b64encode(file_url.encode('utf-8')).decode('utf-8')
    return f"{KKFILEVIEW_URL}/onlinePreview?url={encoded_url}"
