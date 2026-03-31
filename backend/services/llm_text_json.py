"""Normalize LLM output into a JSON object string (fences, prose wrappers)."""
import re


def coerce_llm_json_text(raw: str) -> str:
    t = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1 and j > i:
        return t[i : j + 1]
    return t
