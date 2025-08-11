import json
from datetime import datetime
from llm_client import LLMClient

WEEKDAYS_PT = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo"
]

def _format_when(task: dict) -> str:
    """
    Retorna:
      - ' na terça-feira (11/08/2025) de manhã'
      - ' na terça-feira (11/08/2025)'
      - ' de manhã'
      - '' (se não houver nada)
    """
    dt = task.get("desired_date")
    tw = task.get("time_window")
    parts = []

    if dt:
        try:
            d = datetime.fromisoformat(dt)
            parts.append(f"na {WEEKDAYS_PT[d.weekday()]} ({d.strftime('%d/%m/%Y')})")
        except Exception:
            parts.append(f"no dia {dt}")

    if tw:
        pt = {"morning": "de manhã", "afternoon": "à tarde", "evening": "à noite"}.get(tw, "")
        if pt:
            parts.append(pt)

    return (" " + " ".join(parts)) if parts else ""


class SupplierQuestionNode:
    def __init__(self, tone: str | None = None):
        self.llm = LLMClient()

    def _fallback(self, task: dict, supplier: dict) -> str:
        """Pergunta determinística para cada tipo de serviço."""
        name = supplier.get("name", "fornecedor")
        stype = (task.get("service_type") or "").lower()
        when = _format_when(task)

        if stype == "faucet_repair":
            if when:
                return f"Olá {name}, você consegue consertar uma torneira pingando{when}? Qual seria o preço?"
            return f"Olá {name}, você consegue consertar uma torneira pingando? Se sim, quando e qual seria o preço?"
        elif stype == "tshirt_sale":
            color = task.get("color", "")
            size = task.get("size", "")
            base = f"Olá {name}, você tem camiseta {color} tamanho {size}{when}?"
            return f"{base} Qual seria o preço?"
        else:  
            color = task.get("color", "")
            size = task.get("size", "")
            base = f"Olá {name}, você tem calça {color} tamanho {size}{when}?"
            return f"{base} Qual seria o preço?"

    def run(self, task: dict, supplier: dict) -> str:
        stype = (task.get("service_type") or "").lower()

        if stype == "faucet_repair":
            return self._fallback(task, supplier)

        sys = (
            "Gere UMA pergunta em português do Brasil, sem markdown e sem asteriscos, em tom neutro. "
            "Para roupas, pergunte pelo item com cor/tamanho (se houver) e preço; inclua data/turno se existirem. "
            "Responda apenas com a pergunta."
        )
        payload = {"task": task, "supplier": supplier}
        try:
            q = self.llm.ask(sys, json.dumps(payload, ensure_ascii=False)).strip().replace("\n", " ")
            if not q:
                return self._fallback(task, supplier)
            if stype in {"tshirt_sale", "pants_sale"} and not any(
                w in q.lower() for w in ["camisa", "camiseta", "calça", "tamanho", "preço", "preco"]
            ):
                return self._fallback(task, supplier)
            return q
        except Exception:
            return self._fallback(task, supplier)
