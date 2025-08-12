import json
import re
from llm_client import LLMClient

SIZE_PATTERNS = [
    r"\btam(?:anho)?\s*[:\-]?\s*([x]{0,3}g{1,2}|pp|p|m|g|gg|xg|xxg|xgg|xggg|xl|xxl|xxxl)\b",
    r"\b([x]{0,3}g{1,2}|pp|p|m|g|gg|xg|xxg|xgg|xggg|xl|xxl|xxxl)\b",
    r"\btam(?:anho)?\s*[:\-]?\s*(\d{2})\b",
    r"\b(\d{2})\b",
]
COLOR_PATTERNS = [
    r"\b(preto|preta|branco|branca|azul|vermelh[oa]|verde|amarel[oa]|cinza|rosa|roxo|marrom|bege|lil[aá]s|vinho|bord[oó])\b"
]

def _normalize_size(s: str | None) -> str | None:
    if not s:
        return None
    t = s.lower()
    mapping = {
        "pp": "PP",
        "p": "P",
        "m": "M",
        "g": "G",
        "gg": "GG",
        "xg": "XG",
        "xxg": "XXG",
        "xgg": "XGG",
        "xggg": "XGGG",
        "xl": "GG",
        "xxl": "XG",
        "xxxl": "XXG",
    }
    if t.isdigit():
        return t  
    return mapping.get(t, t.upper())

def _normalize_color(c: str | None) -> str | None:
    if not c:
        return None
    t = c.lower()
    if t in {"preto"}:
        return "preta"
    if t in {"branco"}:
        return "branca"
    return t

def _regex_extract(text: str) -> tuple[str | None, str | None, str]:
    """
    Retorna (color, size, service_type)
    service_type: 'tshirt_sale' se falar camisa/camiseta; 'pants_sale' se falar calça; default 'tshirt_sale'
    """
    t = (text or "").lower()

    if re.search(r"\b(cal[cç]a|pants)\b", t):
        service_type = "pants_sale"
    else:
        service_type = "tshirt_sale"

    size_found = None
    for pat in SIZE_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            size_found = _normalize_size(m.group(1))
            break

    color_found = None
    for pat in COLOR_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            color_found = _normalize_color(m.group(1))
            break

    return color_found, size_found, service_type


class ClothingNormalizerNode:
    def __init__(self):
        self.llm = LLMClient()

    def run(self, task_text: str, current_date: str | None = None) -> dict:
        sys = (
            "You are a strict information extractor. Output ONLY valid JSON with keys:\n"
            "  service_type ('tshirt_sale' or 'pants_sale'),\n"
            "  description (copy of user text),\n"
            "  color (lowercase in pt-BR or null),\n"
            "  size (exact size string present in the text like 'GG','G','M','42' or null),\n"
            "  desired_date (YYYY-MM-DD or null).\n"
            "Rules:\n"
            "- Do NOT invent values. If a field is not explicitly present, use null.\n"
            "- Detect service_type from the item mentioned: camisa/camiseta => 'tshirt_sale'; calça => 'pants_sale'.\n"
            "- If the user uses 'preto'/'branco', normalize to 'preta'/'branca'. Keep other colors lowercase as written.\n"
            "- Sizes may be letter-based (PP,P,M,G,GG,XG,XXG,...) or numeric (e.g., 42). Keep exactly what's in the text.\n"
            "- Portuguese relative dates like 'amanhã', 'depois de amanhã', a weekday name (ex: quinta-feira) may be used.\n"
            f"- Today is {current_date or 'unknown'}; if you compute a date, output ISO 'YYYY-MM-DD'."
        )

        user = json.dumps(
            {"task_text": task_text, "current_date": current_date},
            ensure_ascii=False,
        )

        llm_data = None
        try:
            raw = self.llm.ask(sys, user)
            llm_data = json.loads(raw)
        except Exception:
            llm_data = None

        color_rx, size_rx, service_rx = _regex_extract(task_text)


        data = {
            "service_type": "tshirt_sale",
            "description": task_text,
            "color": None,
            "size": None,
            "desired_date": None,
        }

        if llm_data and isinstance(llm_data, dict):
            stype = llm_data.get("service_type")
            if stype in {"tshirt_sale", "pants_sale"}:
                data["service_type"] = stype
            else:
                data["service_type"] = service_rx  

            data["description"] = llm_data.get("description") or task_text

            c = llm_data.get("color")
            c = _normalize_color(c) if isinstance(c, str) else None
            data["color"] = c or color_rx  

            s = llm_data.get("size")
            s = _normalize_size(s) if isinstance(s, str) or (isinstance(s, int) and str(s).isdigit()) else None
            data["size"] = s or size_rx

            dd = llm_data.get("desired_date")
            if isinstance(dd, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dd):
                data["desired_date"] = dd
            else:
                data["desired_date"] = None
        else:
            data.update(
                {
                    "service_type": service_rx,
                    "color": color_rx,
                    "size": size_rx,
                    "desired_date": None,
                }
            )

        return data
