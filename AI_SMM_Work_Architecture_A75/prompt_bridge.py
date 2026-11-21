# -*- coding: utf-8 -*-
"""RU->EN prompt bridge via local LLM. Spec-generator mode. Ollama primary (auto-unload VRAM),
LM Studio fallback. Returns ONE English prompt string (positive + inline avoid-tags)."""
import json, re, urllib.request, logging
log = logging.getLogger(__name__)
OLLAMA_URL = "http://localhost:11434/api/generate"
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"

SYSTEM = (
"You are a prompt engineer for Stable Diffusion XL. Turn the user's image request (ANY language) "
"into ONE dense, specific English prompt. Do NOT just translate — build a full specification.\n"
"Rules:\n"
"1. MATERIALS: pick the correct real-world material for the subject; never invent a wrong one. "
"For a tennis/sports court choose exactly one of: 'acrylic hard court surface' (green inner / "
"blue or red outer, crisp white lines), 'clay court' (orange-red, white lines), or 'grass court' "
"(mown green, white lines). NEVER say concrete, asphalt, stone, or mixed/patchy ground for a court. "
"For interiors/products/food name the true surfaces (wood, marble, ceramic, fabric, metal).\n"
"2. GEOMETRY & STRUCTURE: if the scene has a regulated layout, describe it precisely so the model "
"draws it correctly. Tennis court example: 'a regulation rectangular court, two equal halves "
"divided by a taut net stretched across the center, parallel baselines and service lines receding "
"in correct one-point perspective, net posts at the sidelines'. Keep lines straight and parallel.\n"
"3. LIGHTING / CAMERA / STYLE: state time-of-day light, lens and depth-of-field, and a style tag "
"(photorealistic / documentary / editorial).\n"
"4. RESPECT NEGATIVES IN THE REQUEST: if the user says 'without people / no people', make sure "
"'no people' is honored and do NOT add any human. Carry over every explicit exclusion.\n"
"5. INLINE AVOID-TAGS: append a short clause that blocks common hallucinations for THIS subject, "
"e.g. 'no light poles inside the playing area, no solid wall in place of the net, no floating "
"objects, no warped perspective, no text, no watermark, no logo'.\n"
"6. OUTPUT: ONLY the final prompt text. No quotes, no preamble, no bullet list, no explanation, "
"no < think> blocks. One paragraph, comma-separated descriptors, 40-90 words."
)

def _clean(t):
    t = (t or "").strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S | re.I).strip()
    t = re.sub(r"^(prompt|final prompt|specification)\s*[:\-]\s*", "", t, flags=re.I)
    t = t.strip('\"').strip("'").strip()
    return t

def _post(url, payload, timeout=120):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def _via_ollama(model, user_text):
    resp = _post(OLLAMA_URL, {"model": model, "system": SYSTEM, "prompt": user_text,
                              "stream": False, "keep_alive": 0})
    return _clean(resp.get("response"))

def _via_lmstudio(model, user_text):
    resp = _post(LMSTUDIO_URL, {"model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}],
        "temperature": 0.4, "max_tokens": 400, "stream": False})
    return _clean(resp["choices"][0]["message"]["content"])

def translate_to_prompt(ru_text, ollama_model="qwen3:8b", lmstudio_model="qwen2.5-7b-instruct"):
    try:
        out = _via_ollama(ollama_model, ru_text)
        if out:
            log.info("bridge(spec) via Ollama/%s -> %s", ollama_model, out[:240])
            return out
    except Exception as e:
        log.warning("Ollama bridge failed: %s", e)
    try:
        out = _via_lmstudio(lmstudio_model, ru_text)
        if out:
            log.info("bridge(spec) via LMStudio/%s -> %s", lmstudio_model, out[:240])
            return out
    except Exception as e:
        log.warning("LMStudio bridge failed: %s", e)
    log.warning("bridge unavailable -> raw RU text to SDXL (expect degraded output)")
    return ru_text
