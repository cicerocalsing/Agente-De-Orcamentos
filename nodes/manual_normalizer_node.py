import json, re
from datetime import date, timedelta
from llm_client import LLMClient

WEEKDAY_MAP = {
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terça": 1, "terca": 1, "terça-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sábado": 5, "sabado": 5, "sáb": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}

def _next_weekday(base: date, wd: int) -> date:
    d = (wd - base.weekday() + 7) % 7
    return base + timedelta(days=d or 7)

class ManualNormalizerNode:
    def __init__(self):
        self.llm = LLMClient()

    def _infer_time_window(self, text: str) -> str | None:
        t = (text or "").lower()
        if any(k in t for k in ["manhã", "manha", "cedo"]):
            return "morning"
        if "tarde" in t:
            return "afternoon"
        if any(k in t for k in ["noite", "final do dia", "fim do dia"]):
            return "evening"
        return None

    def _infer_date(self, text: str, current_date: str | None) -> str | None:
        """Faço inferência APENAS se houver termos explícitos."""
        if not current_date:
            return None
        base = date.fromisoformat(current_date)
        t = (text or "").lower()

        if "depois de amanhã" in t or "depois de amanha" in t:
            return (base + timedelta(days=2)).isoformat()
        if "amanhã" in t or "amanha" in t:
            return (base + timedelta(days=1)).isoformat()
        if "hoje" in t:
            return base.isoformat()

        for token, wd in WEEKDAY_MAP.items():
            if re.search(rf"\b{token}\b", t):
                return _next_weekday(base, wd).isoformat()

        return None

    def run(self, task_text: str, current_date: str | None = None) -> dict:
        sys = (
            "Extraia JSON de uma tarefa manual com as chaves: "
            "service_type (faucet_repair), description, location (se houver), desired_date (YYYY-MM-DD ou null). "
            "Não invente valores. Responda apenas JSON."
        )
        raw = self.llm.ask(sys, f"current_date={current_date}\nTask: {task_text}")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"service_type": "faucet_repair", "description": task_text, "location": None, "desired_date": None}

        data["time_window"] = self._infer_time_window(task_text)

        if not data.get("desired_date"):
            inferred = self._infer_date(task_text, current_date)
            data["desired_date"] = inferred

        return data
