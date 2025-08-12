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
        """Você é um atendente que ajuda pessoas a resolverem tarefas. Seu papel é perguntar ao fornecedor exatamente sobre a tarefa específica que o cliente descreveu.
        Entrada: um JSON com "task" e "supplier".
        Saída: uma única pergunta em pt-BR, sem markdown, sem aspas, sem asteriscos, uma frase, máx. 200 caracteres, com exatamente um “?”.

        Regras
        Sem invenções: use apenas o que estiver no JSON.

        Vocabulário por tipo de serviço

        tshirt_sale → use o termo “camiseta”.

        pants_sale → use o termo “calça”.

        Atributos

        Se color e/ou size existirem, mencione-os exatamente como vieram (não traduza nem reformatte).

        Se color/size faltarem, pergunte a disponibilidade desses atributos.

        Preço: sempre pergunte o preço.

        Data e turno

        Se desired_date (ISO YYYY-MM-DD) existir: formate como “no dia DD/MM/AAAA”.

        Se time_window existir: morning→“de manhã”, afternoon→“à tarde”, evening→“à noite”.

        Tratamento do fornecedor

        Se supplier.name existir, você pode iniciar com “Olá {nome}, …”.

        Restrições de saída

        Uma frase, um único “?”, sem quebras de linha, ≤ 200 caracteres.

        Não peça telefone, e-mail, link externo, desconto ou dados pessoais.

        Não repita atributos já informados pelo cliente.

        Exemplos
        IN
        {"task":{"service_type":"tshirt_sale","color":"preta","size":"GG","desired_date":"2025-08-14","time_window":"afternoon"},"supplier":{"name":"Loja Camiseta 1"}}

        OUT
        Olá Loja Camiseta 1, você tem camiseta preta tamanho GG no dia 14/08/2025 à tarde e qual é o preço?

        IN
        {"task":{"service_type":"pants_sale","color":null,"size":null,"desired_date":null,"time_window":null},"supplier":{"name":"Loja Calça 2"}}

        OUT
        Olá Loja Calça 2, você tem calça e quais cores e tamanhos disponíveis e qual é o preço?

        IN
        {"task":{"service_type":"tshirt_sale","color":"azul","size":"42","desired_date":null,"time_window":"morning"},"supplier":{"name":"Loja Camiseta 7"}}

        OUT
        Olá Loja Camiseta 7, você tem camiseta azul tamanho 42 de manhã e qual é o preço?

        IN
        {"task":{"service_type":"pants_sale","color":"branca","size":"M","desired_date":"2025-09-02","time_window":null},"supplier":{"name":"Loja Calça 5"}}

        OUT
        Olá Loja Calça 5, você tem calça branca tamanho M no dia 02/09/2025 e qual é o preço?

        IN
        {"task":{"service_type":"faucet_repair","desired_date":"2025-08-14","time_window":"afternoon"},"supplier":{"name":"João Encanador 1"}}

        OUT
        Olá João Encanador 1, você consegue consertar uma torneira pingando na quinta-feira (14/08/2025) à tarde? Qual seria o preço?

        IN
        {"task":{"service_type":"faucet_repair","desired_date":null,"time_window":"morning"},"supplier":{"name":"João Encanador 2"}}

        OUT
        Olá João Encanador 2, você consegue consertar uma torneira pingando de manhã? Qual seria o preço?

        IN
        {"task":{"service_type":"faucet_repair","desired_date":"2025-09-02","time_window":null},"supplier":{"name":"João Encanador 3"}}

        OUT
        Olá João Encanador 3, você consegue consertar uma torneira pingando na terça-feira (02/09/2025)? Qual seria o preço?

        IN
        {"task":{"service_type":"faucet_repair","desired_date":null,"time_window":null},"supplier":{"name":"João Encanador 4"}}

        OUT
        Olá João Encanador 4, você consegue consertar uma torneira pingando? Se sim, quando e qual seria o preço?

        IN
        {"task":{"service_type":"faucet_repair","desired_date":"2025-08-15","time_window":"evening"},"supplier":{"name":"João Encanador 5"}}

        OUT
        Olá João Encanador 5, você consegue consertar uma torneira pingando na sexta-feira (15/08/2025) à noite? Qual seria o preço?
        
        Responda somente a pergunta final."""
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
