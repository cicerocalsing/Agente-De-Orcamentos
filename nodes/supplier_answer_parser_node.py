import json, re
from datetime import date, timedelta, datetime
from llm_client import LLMClient
from db.mongo import db

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

def _safe_date(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None

def _parse_date_from_text(text: str, current_date: str | None) -> str | None:
    """
    Suporta:
      - YYYY-MM-DD / YYYY/MM/DD
      - dd/mm(/aa|aaaa)  (default)
      - mm/dd(/aa|aaaa)  (heurística quando o 2º número > 12)
      - amanhã / hoje / depois de amanhã
      - nomes de dias da semana
    """
    t = (text or "").lower()
    base = date.fromisoformat(current_date) if current_date else None

    m_iso = re.search(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b", t)
    if m_iso:
        y = int(m_iso.group(1)); m = int(m_iso.group(2)); d = int(m_iso.group(3))
        out = _safe_date(y, m, d)
        if out: 
            return out

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        ytxt = m.group(3)

        if ytxt:
            y = int(ytxt)
            if y < 100:  
                y += 2000
        else:
            y = base.year if base else date.today().year


        if b > 12 and a <= 12:
            mth, day = a, b
        else:
            day, mth = a, b

        out = _safe_date(y, mth, day)
        if out:
            return out

    if base:
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

class SupplierAnswerParserNode:
    def __init__(self):
        self.llm = LLMClient()

    def run(self, task: dict, supplier: dict, answer: str) -> dict:
        system = (
            "Você recebe a TAREFA do cliente e a RESPOSTA do fornecedor. "
            "Decida se o fornecedor consegue atender (can_do). "
            "Se a tarefa tiver data/turno, aceite somente se a resposta for compatível. "
            "Extraia o preço como número (price). Se o fornecedor mencionar uma data, inclua em supplier_date."
            "Responda APENAS JSON: "
            "{"
            "  \"can_do\": true|false, "
            "  \"meets_date\": true|false|null, "
            "  \"meets_time_window\": true|false|null, "
            "  \"price\": number|null, "
            "  \"supplier_date\": string|null, "
            "  \"notes\": string"
            "}"
        )

        payload = {
            "task": {
                "service_type": task.get("service_type"),
                "description": task.get("description"),
                "desired_date": task.get("desired_date"),
                "time_window": task.get("time_window"),
                "location": task.get("location"),
            },
            "supplier": {"name": supplier.get("name"), "id": supplier.get("id")},
            "answer": answer,
        }

        try:
            raw = self.llm.ask(system, json.dumps(payload, ensure_ascii=False))
            data = json.loads(raw)
        except Exception:
            data = {"can_do": False, "price": None, "supplier_date": None, "notes": answer,
                    "meets_date": None, "meets_time_window": None}

        can_do = bool(data.get("can_do"))
        price = data.get("price")
        try:
            price = float(price) if price is not None else None
        except Exception:
            price = None

        desired = task.get("desired_date")
        timew = task.get("time_window")
        meets_date = data.get("meets_date")
        meets_tw = data.get("meets_time_window")

        if desired is not None:
            can_do = can_do and (meets_date is True)
        if timew is not None:
            can_do = can_do and (meets_tw is True)

        supplier_date_raw = data.get("supplier_date")
        supplier_date_iso = _parse_date_from_text(supplier_date_raw or answer, task.get("current_date"))

        accepted = bool(can_do and (price is not None))
        offer = None
        if accepted:
            offer = {
                "name": supplier.get("name"),
                "price": price,
                "available_date": desired or supplier_date_iso or "-",
                "lead_time_days": None,
                "notes": data.get("notes") or answer,
            }

            try:
                db.offers.insert_one({
                    "run_id": task.get("run_id"),
                    "created_at": datetime.utcnow(),
                    "supplier": {
                        "id": supplier.get("id"),
                        "name": supplier.get("name"),
                    },
                    "task": {
                        "service_type": task.get("service_type"),
                        "description": task.get("description"),
                        "desired_date": task.get("desired_date"),
                        "time_window": task.get("time_window"),
                        "location": task.get("location"),
                        "current_date": task.get("current_date"),
                    },
                    "offer": offer
                })
            except Exception:
                pass

        return {"accepted": bool(offer), "need_more": not bool(offer), "offer": offer}
