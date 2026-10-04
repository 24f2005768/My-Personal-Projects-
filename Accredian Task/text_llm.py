"""
Shared text/JSON LLM helper for Phase 2 (menu analysis, AOV insights).

Tries Gemini first (kept as the default text provider), and falls back to
Groq automatically if Gemini comes back empty — in practice this almost
always means Gemini's free-tier daily quota was hit (20 requests/day on
gemini-3.6-flash per your run.log). Groq's free tier is tracked separately
per-model, so a request that Gemini can't serve today still has a real
chance of succeeding on Groq.

Phase 2 only needs two of these calls per run (menu analysis + AOV
insights), so this is intentionally simple — no need for anything fancier
than "try A, then try B."
"""
from agent.logger import log
from agent import gemini_client
from agent import groq_client


def call_json_with_fallback(prompt: str,
                             gemini_model: str = None,
                             groq_model: str = None,
                             max_retries: int = 3) -> dict:
    result = gemini_client.call_json(prompt, model_name=gemini_model, max_retries=max_retries)
    if result:
        return result

    log.warning("Gemini call_json returned no usable result — falling back to Groq.")
    result = groq_client.call_json(prompt, model_name=groq_model, max_retries=max_retries)
    if result:
        log.info("Groq fallback succeeded.")
    else:
        log.error("Groq fallback also returned no usable result — see warnings above for both providers.")
    return result