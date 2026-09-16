import os
import re
import time
from typing import List, Dict, Optional

from cache import ResponseCache
from observability import log_llm_call


PII_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    re.compile(r'\b\d{10,11}\b'),
    re.compile(r'\b\d{6,10}\b'),
]


RESTRICTED_WORDS = [
    'asesino', 'suicidio', 'suicidarme', 'matar', 'arma', 'drogas', 'cocaina', 'marihuana',
    'diagnostico medico', 'tratamiento medico', 'demanda legal', 'abogado', 'demandar'
]


def _sanitize_text(text: str) -> str:
    for patron in PII_PATTERNS:
        text = patron.sub('[DATO PROTEGIDO]', text)
    return text


def _moderate_text(text: str, api_key: str = None, provider: str = None) -> bool:
    """Moderacion externa con OpenAI si esta disponible."""
    if provider != "openai" or not api_key:
        return True
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        result = client.moderations.create(input=text)
        for r in result.results:
            if r.flagged:
                return False
    except Exception:
        return True
    return True


def _format_context(results: List[Dict]) -> str:
    lines = []
    for r in results:
        content = _sanitize_text(r['content'])
        lines.append(f"- {r['category']}: {content}")
    return "\n".join(lines)


def _build_prompt(query: str, context: str) -> str:
    return (
        "Eres un asistente de ESIC Medellín. Responde en español de forma clara, profesional y concisa. "
        "Usa ÚNICAMENTE la información del contexto. Si no sabes la respuesta, indica que se derivará con un asesor humano.\n\n"
        f"Contexto:\n{context}\n\n"
        f"Pregunta del egresado: {query}\n\n"
        "Respuesta:"
    )


def _template_response(query: str, results: List[Dict], sources: str) -> str:
    if not results:
        return (
            "No encontré información suficiente para responder esa consulta. "
            "Te estoy derivando con un asesor de ESIC que te contactará pronto."
        )

    top = results[0]
    category = top["category"]

    if "programa" in query.lower() or "especialización" in query.lower() or category == "programas":
        intro = "Estas son las opciones de especialización que encontré para ti:"
        bullets = []
        for r in results[:3]:
            m = r["metadata"]
            bullets.append(
                f"• **{m.get('nombre', m.get('cargo', 'Opción'))}** — {m.get('modalidad', '')} {m.get('duracion', '')}. {m.get('descripcion', '')}"
            )
        return f"{intro}\n" + "\n".join(bullets) + f"\n\n_Fuentes consultadas:_ {sources}"

    if "financiamiento" in query.lower() or "pagar" in query.lower() or category == "financiamiento":
        intro = "Tienes estas alternativas de financiamiento:"
        bullets = []
        for r in results[:3]:
            m = r["metadata"]
            bullets.append(
                f"• **{m.get('nombre', '')}**: {m.get('descripcion', '')} Requisito: {m.get('requisitos', '')}"
            )
        return f"{intro}\n" + "\n".join(bullets) + f"\n\n_Fuentes consultadas:_ {sources}"

    if "trabajo" in query.lower() or "empleo" in query.lower() or "oportunidad" in query.lower() or category == "oportunidades":
        intro = "Encontré estas oportunidades laborales relacionadas:"
        bullets = []
        for r in results[:3]:
            m = r["metadata"]
            bullets.append(
                f"• **{m.get('cargo', '')}** en {m.get('empresa', '')} ({m.get('ubicacion', '')}). "
                f"Sector: {m.get('sector', '')}. Rango salarial: ${m.get('salario_min_cop', 0):,} - ${m.get('salario_max_cop', 0):,} COP."
            )
        return f"{intro}\n" + "\n".join(bullets) + f"\n\n_Fuentes consultadas:_ {sources}"

    intro = "Basado en la información institucional, esto es lo que puedo compartirte:"
    bullets = [f"• {r['content']}" for r in results[:3]]
    return f"{intro}\n" + "\n".join(bullets) + f"\n\n_Fuentes consultadas:_ {sources}"


def _call_openai(prompt: str, api_key: str, model: str = "gpt-3.5-turbo") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def _call_provider(prompt: str, provider: str, api_key: str, model: str) -> str:
    if provider == "openai":
        return _call_openai(prompt, api_key, model)
    if provider == "mistral":
        return _call_mistral(prompt, api_key, model)
    if provider == "groq":
        return _call_groq(prompt, api_key, model)
    raise ValueError(f"Proveedor {provider} no soportado")


def _call_mistral(prompt: str, api_key: str, model: str = "mistral-tiny") -> str:
    import httpx
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_groq(prompt: str, api_key: str, model: str = "llama3-8b-8192") -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def _fallback_chain(
    prompt: str,
    providers: List[str],
    api_keys: Dict[str, str],
    models: Dict[str, str],
) -> tuple:
    """Intenta llamar a cada proveedor en orden. Retorna (respuesta, proveedor usado, error)."""
    last_error = ""
    for p in providers:
        if not api_keys.get(p):
            continue
        try:
            answer = _call_provider(prompt, p, api_keys[p], models.get(p, ""))
            return answer, p, ""
        except Exception as e:
            last_error = f"{p}: {e}"
    return "", "", last_error


def _filter_by_intent(query: str, results: List[Dict]) -> List[Dict]:
    q = query.lower()
    intent_map = {
        "programas": ["programa" in q, "especialización" in q, "posgrado" in q, "pregrado" in q, "mercadeo" in q, "marketing" in q],
        "financiamiento": ["financiamiento" in q, "pagar" in q, "crédito" in q, "convenio" in q, "beca" in q],
        "oportunidades": ["trabajo" in q, "empleo" in q, "oportunidad" in q, "laboral" in q, "cargo" in q],
    }
    for category, checks in intent_map.items():
        if any(checks):
            filtered = [r for r in results if r["category"] == category]
            if filtered:
                return filtered
            # Fallback: buscar directamente en el dataset si el vector store no trajo resultados
            return direct_search(query, category)
    return results


def direct_search(query: str, category: str) -> List[Dict]:
    """Búsqueda directa por palabras clave en dummy_data.json."""
    from vector_store import load_dummy_data
    q = query.lower()
    docs = [d for d in load_dummy_data() if d["category"] == category]

    if category == "programas" and ("mercadeo" in q or "marketing" in q):
        docs = [d for d in docs if any(term in d["content"].lower() for term in ["mercadeo", "marketing"])]

    if not docs:
        return []

    return [
        {
            "id": d["id"],
            "category": d["category"],
            "content": d["content"],
            "metadata": d["metadata"],
            "score": 1.0,
        }
        for d in docs[:5]
    ]


def generate_response(
    query: str,
    results: List[Dict],
    session_id: str,
    provider: str = "local",
    api_key: str = None,
    model: str = None,
    cache: Optional[ResponseCache] = None,
) -> tuple:
    """Genera una respuesta usando el proveedor de LLM seleccionado, caché y fallback automático. Retorna (answer, trace_id)."""
    results = _filter_by_intent(query, results)
    sources = ", ".join(sorted(set(r["category"] for r in results))) if results else "ninguna"
    context = _format_context(results)
    prompt = _build_prompt(query, context)
    trace_id = None

    # 1. Revisar caché
    if cache:
        cached = cache.get(query, provider, model or "")
        if cached:
            return f"{cached['answer']}\n\n_(Respuesta recuperada de caché)_", trace_id

    # 2. Respuesta local
    if provider == "local" or not api_key:
        answer = _template_response(query, results, sources)
        if cache:
            cache.set(query, provider, model or "", {"answer": answer})
        return answer, trace_id

    # 3. Moderacion externa si aplica
    if provider != "local" and api_key and not _moderate_text(query, api_key, provider):
        answer = _template_response(query, results, sources)
        if cache:
            cache.set(query, provider, model or "", {"answer": answer})
        return answer, trace_id

    # 4. Llamada a LLM con fallback
    providers = [provider, "openai", "mistral", "groq"]
    api_keys = {
        provider: api_key,
        "openai": os.environ.get("OPENAI_API_KEY", ""),
        "mistral": os.environ.get("MISTRAL_API_KEY", ""),
        "groq": os.environ.get("GROQ_API_KEY", ""),
    }
    # Si la clave ingresada pertenece a un provider distinto del elegido, intentar con ella
    api_keys[provider] = api_key
    models = {
        "openai": model or "gpt-3.5-turbo",
        "mistral": model or "mistral-tiny",
        "groq": model or "llama3-8b-8192",
    }

    start = time.time()
    try:
        answer, used_provider, error = _fallback_chain(prompt, providers, api_keys, models)
        if not answer:
            answer = _template_response(query, results, sources)
            if error:
                answer += f"\n\n_(No fue posible usar LLM: {error})_"
            status = "partial" if not error else "ok"
        else:
            status = "ok"
            used_provider = used_provider or provider
    except Exception as e:
        answer = _template_response(query, results, sources)
        answer += f"\n\n_(Error inesperado: {e})_"
        used_provider = provider
        status = "error"
        error = str(e)

    latency_ms = int((time.time() - start) * 1000)

    # 4. Guardar trace
    trace_id = log_llm_call(
        session_id=session_id,
        provider=used_provider,
        model=models.get(used_provider, model or ""),
        prompt=_sanitize_text(prompt),
        response=answer,
        latency_ms=latency_ms,
        status=status,
        error_message=error if status != "ok" else "",
    )

    # 5. Validar salida por politicas
    answer = _sanitize_text(answer)
    lower = answer.lower()
    for w in RESTRICTED_WORDS:
        if w in lower:
            answer = "No puedo responder sobre ese tema. Te recomiendo acudir a un profesional calificado."
            break

    # 6. Guardar en caché
    if cache:
        cache.set(query, provider, model or "", {"answer": answer})

    return answer, trace_id
