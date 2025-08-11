from llm_client import LLMClient

MANUAL_HINTS = [
    "torneira", "encanador", "hidrául", "hidraul", "pia", "cano",
    "vazando", "vazamento", "chuveiro", "registro", "conserto",
]
CLOTHING_HINTS = [
    "camisa", "camiseta", "t-shirt", "tshirt", "blusa",
    "calça", "calca", "pants", "roupa", "tamanho", "cor",
]

class ClassifierNode:
    def __init__(self):
        self.llm = LLMClient()

    def _heuristic(self, text: str) -> str:
        t = (text or "").lower()
        if any(k in t for k in MANUAL_HINTS):
            return "manual_process"
        if any(k in t for k in CLOTHING_HINTS):
            return "clothing"
        return "manual_process"  

    def run(self, task_text: str) -> dict:
        label = self._heuristic(task_text)

        sys = (
            "Return ONLY one label: 'manual_process' or 'clothing'. "
            "If the task mentions plumbing, faucet, leaks, or similar, choose 'manual_process'. "
            "If the task mentions shirts, pants, clothing, sizes or colors, choose 'clothing'. "
            "Do not rewrite the task. Output ONLY the label."
        )
        try:
            out = self.llm.ask(sys, f"Task: {task_text}").strip().lower()
            if out in {"manual_process", "clothing"}:
                label = out
        except Exception:
            pass

        return {"category": label, "original_task": task_text}
