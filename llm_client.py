import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
load_dotenv()
class LLMClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3")
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = ChatOllama(model=self.model, base_url=base_url)
    def ask(self, system_prompt: str, user_prompt: str) -> str:
        resp = self.client.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return resp.content.strip()
