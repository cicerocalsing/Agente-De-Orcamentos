import json
from llm_client import LLMClient
class SupplierFollowupNode:
    def __init__(self): self.llm = LLMClient()
    def run(self, task: dict, supplier: dict, transcript: list[dict]) -> str | None:
        sys=(
            "Você recebe o histórico de mensagens entre atendente e fornecedor. "
            "Se ainda faltarem informações essenciais para decidir (por exemplo, preço não informado, "
            "disponibilidade na data/período ainda não confirmada), gere UMA pergunta de follow-up. "
            "Caso já esteja claro que atende com preço informado e no prazo (quando houver), responda exatamente 'STOP'. "
            "Sem markdown. Responda com a pergunta ou 'STOP'."
        )
        usr=json.dumps({'task':task,'supplier':supplier,'history':transcript}, ensure_ascii=False)
        out=self.llm.ask(sys, usr).strip()
        return out
