from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)



SYSTEM_PROMPT_TEMPLATE = """You are Gravity, an expert, encouraging, and highly effective STEM AI tutor on the EklavyaX learning platform.

Your mission: Provide clear, accurate, and deeply understandable explanations that directly and precisely answer what the student is asking or studying.

TUTORING GUIDELINES:
1. DIRECT ANSWER FIRST (MANDATORY):
   - Always begin by directly and explicitly answering the student's exact question in the very first sentence.
   - If the student asks for a count, definition, formula, or specific fact (e.g. "how many newton law?", "what is velocity?", "state Ohm's law"), immediately provide the exact number, formula, or factual answer.
   - NEVER dodge the question, and NEVER use phrases like "Instead of giving you a number/answer...". Always state the answer directly.
2. STRUCTURED STEP-BY-STEP BREAKDOWN:
   - For multiple laws, parts, or steps, list each one with bold numbering and clear titles (e.g. **1. First Law (Law of Inertia)**, **2. Second Law (F = ma)**, **3. Third Law (Action & Reaction)**).
   - State the core definition and formula clearly for each part.
3. INTUITIVE REAL-WORLD ANALOGIES:
   - Provide a relatable, intuitive real-world example or analogy (e.g. sports, daily life, science) to make the concept stick.
4. TARGET LANGUAGE:
   - Write your complete response in {target_language}. (If "Simple English" or "English", use clean, clear English).
5. ENCOURAGING CLOSING:
   - Conclude with a brief, motivating remark.
6. MATH & FORMULA FORMATTING (CRITICAL):
   - ALWAYS write mathematical formulas, equations, and symbols using LaTeX notation wrapped in dollar-sign delimiters.
   - For inline math (within a sentence), use single dollar signs: $F = ma$, $E = mc^2$, $\\neg(A \\land B)$
   - For display math (standalone equation on its own line), use double dollar signs: $$F = ma$$
   - Use proper LaTeX commands for symbols: $\\cap$ for intersection, $\\cup$ for union, $\\neg$ for negation, $\\land$ for AND, $\\lor$ for OR, $\\iff$ for if and only if, $\\implies$ for implies, $\\frac{{a}}{{b}}$ for fractions, $\\sqrt{{x}}$ for square root, $\\int$ for integral, $\\sum$ for summation, etc.
   - NEVER write raw LaTeX commands as plain text. Always wrap them in $ delimiters so they render as beautiful formatted math.
   - Example: Write $A^c \\cup B^c$ NOT "A^c \\cup B^c" without dollar signs.

Student Question / Topic:
\"\"\"
{highlighted_text}
\"\"\"

Your explanation:"""


def build_explanation_prompt(highlighted_text: str, target_language: str) -> str:
    """
    Build the full system prompt for the AI explanation request.

    Args:
        highlighted_text: Text selected by the student.
        target_language: Language requested (e.g. "Hindi", "Simple English").

    Returns:
        Formatted prompt string.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(
        highlighted_text=highlighted_text.strip(),
        target_language=target_language.strip(),
    )


# ── Provider: Groq Cloud ──────────────────────────────────────────────────────

GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "qwen/qwen3.6-27b",
]


async def _call_groq(prompt: str) -> str:
    """
    Call the Groq Cloud Chat Completions API (ultra-fast LPU inference).

    Includes model fallback across Groq's high-speed free tier models.

    Raises:
        HTTPException 503 if API key is missing.
        HTTPException 502 on API failure.
        HTTPException 429 if rate-limited.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API key not configured. Contact the administrator or set GROQ_API_KEY in .env.",
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    models_to_try = []
    if settings.GROQ_MODEL:
        models_to_try.append(settings.GROQ_MODEL)
    for fb_model in GROQ_FALLBACK_MODELS:
        if fb_model not in models_to_try:
            models_to_try.append(fb_model)

    last_status = None
    rate_limited_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 3500,
            }

            try:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 429:
                    rate_limited_count += 1
                    last_status = 429
                    logger.warning("Groq model '%s' rate-limited (429). Trying fallback...", model)
                    continue

                if response.status_code in (400, 404, 502, 503):
                    logger.warning("Groq model '%s' returned %d. Trying next model...", model, response.status_code)
                    last_status = response.status_code
                    continue

                response.raise_for_status()

                data = response.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0] and choices[0]["message"].get("content"):
                    raw_content = choices[0]["message"]["content"]
                    # Strip <think>...</think> tags if model includes them
                    import re
                    clean_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
                    return clean_content or raw_content
                else:
                    logger.warning("Empty response from Groq model %s: %s", model, data)
                    continue

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning("Error with Groq model '%s': %s", model, exc)
                continue

    if rate_limited_count > 0 and last_status == 429:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI is busy right now (rate-limited). Please wait a moment and try again.",
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI provider (Groq) is currently unavailable. Please try again in a moment.",
    )



OPENROUTER_FALLBACK_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "z-ai/glm-5.2:free",
    "google/gemma-4-31b-it:free",
]


async def _call_openrouter(prompt: str) -> str:
    """
    Call the OpenRouter Chat Completions API and return the generated text.

    Includes automatic model fallback and retry for 429 rate-limit errors
    or model unavailabilities common on free tier endpoints.

    Raises:
        HTTPException 503 if API key is missing.
        HTTPException 502 on API failure.
        HTTPException 429 if rate-limited after all retries and fallback models.
    """
    if not settings.OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter API key not configured. Contact the administrator.",
        )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://eklavyax.local",
        "X-Title": "EklavyaX Gravity AI Tutor",
    }

    # Build prioritized list of models to try
    models_to_try = []
    if settings.OPENROUTER_MODEL:
        models_to_try.append(settings.OPENROUTER_MODEL)
    for fb_model in OPENROUTER_FALLBACK_MODELS:
        if fb_model not in models_to_try:
            models_to_try.append(fb_model)

    last_status = None
    rate_limited_count = 0

    async with httpx.AsyncClient(timeout=45.0) as client:
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 800,
            }

            for attempt in range(2):
                try:
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code == 429:
                        rate_limited_count += 1
                        last_status = 429
                        logger.warning(
                            "OpenRouter model '%s' returned 429 (attempt %d). Trying fallback...",
                            model, attempt + 1
                        )
                        if attempt == 0:
                            import asyncio
                            await asyncio.sleep(1.0)
                            continue
                        # If attempt 1 also 429, switch to next model immediately
                        break

                    if response.status_code in (404, 502, 503):
                        logger.warning(
                            "OpenRouter model '%s' returned %d. Trying next fallback model...",
                            model, response.status_code
                        )
                        last_status = response.status_code
                        break

                    response.raise_for_status()

                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0] and choices[0]["message"].get("content"):
                        return choices[0]["message"]["content"]
                    else:
                        logger.warning("Empty response from model %s: %s", model, data)
                        break

                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    logger.warning("Error with model '%s': %s", model, exc)
                    break

    if rate_limited_count > 0 and last_status == 429:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI is busy right now (rate-limited). Please wait a moment and try again.",
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI provider (OpenRouter) is currently unavailable. Please try again in a moment.",
    )



async def _call_gemini(prompt: str) -> str:
    """
    Call the Google Gemini API and return the generated text.

    Raises:
        HTTPException 502 on API failure.
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key not configured. Contact the administrator.",
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
            "topP": 0.9,
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Gemini API HTTP error: %s – %s", exc.response.status_code, exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider (Gemini) returned an error: {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        logger.error("Gemini API request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to AI provider (Gemini). Try again later.",
        )

    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Gemini response structure: %s", data)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an unexpected response format.",
        )




async def _call_openai(prompt: str) -> str:
    """
    Call the OpenAI Chat Completions API and return the generated text.

    Raises:
        HTTPException 502 on API failure.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured. Contact the administrator.",
        )

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("OpenAI API HTTP error: %s – %s", exc.response.status_code, exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider (OpenAI) returned an error: {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        logger.error("OpenAI API request error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to AI provider (OpenAI). Try again later.",
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected OpenAI response structure: %s", data)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an unexpected response format.",
        )


async def get_explanation(highlighted_text: str, target_language: str = "Simple English") -> str:
    """
    Main entry point: build prompt and call the configured AI provider with
    cross-provider fallback if multiple API keys are available.

    Args:
        highlighted_text: Student-selected text from the learning material.
        target_language: Desired response language.

    Returns:
        AI-generated explanation string.

    Raises:
        HTTPException 429/502/503 on unrecoverable failure.
    """
    prompt = build_explanation_prompt(highlighted_text, target_language)

    provider = settings.AI_PROVIDER.lower()


    provider_order = [provider]
    if provider != "groq" and settings.GROQ_API_KEY:
        provider_order.append("groq")
    if provider != "gemini" and settings.GEMINI_API_KEY:
        provider_order.append("gemini")
    if provider != "openrouter" and settings.OPENROUTER_API_KEY:
        provider_order.append("openrouter")
    if provider != "openai" and settings.OPENAI_API_KEY:
        provider_order.append("openai")

    last_exception = None

    for p in provider_order:
        try:
            if p == "groq":
                return await _call_groq(prompt)
            elif p == "gemini":
                return await _call_gemini(prompt)
            elif p == "openrouter":
                return await _call_openrouter(prompt)
            elif p == "openai":
                return await _call_openai(prompt)
        except HTTPException as exc:
            logger.warning("Provider '%s' failed with status %d: %s. Trying next provider...", p, exc.status_code, exc.detail)
            last_exception = exc
        except Exception as exc:
            logger.error("Unexpected error with provider '%s': %s", p, exc)
            last_exception = HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {exc}",
            )

    if last_exception:
        raise last_exception

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"No working AI provider configured. Set AI_PROVIDER or check API keys.",
    )



QUIZ_GEN_PROMPT_TEMPLATE = """You are an expert STEM quiz and competitive exam creator (covering Physics, Chemistry, Mathematics, Biology, Computer Science).
Generate exactly {num_questions} fresh, unique, challenging multiple-choice questions on the topic: "{topic}".
Random Seed / Variation: {seed}
Rules:
- Generate completely new and creative questions (do not repeat standard trivial examples).
- Include interesting calculations, conceptual paradoxes, and practical applications.
- Provide a clear, educational explanation for why the correct option is right.

CRITICAL MATH FORMATTING RULES (MUST FOLLOW):
- Do NOT use LaTeX notation. No dollar signs ($), no backslash commands (\\frac, \\left, \\right, \\log, \\sqrt, \\times, \\cdot, \\theta, \\pi, \\alpha, \\beta, \\infty, etc.).
- Write all math using plain text and Unicode symbols:
  - Fractions: write "n/2" or "(n/2)" instead of \\frac{{n}}{{2}}
  - Exponents: use Unicode superscripts: ² ³ ⁴ ⁵ ⁶ ⁷ ⁸ ⁹ ⁿ (e.g. "n²" not "n^2" or "n^{{2}}")
  - Subscripts: use Unicode subscripts: ₀ ₁ ₂ ₃ ₄ (e.g. "log₂" not "\\log_2")
  - Square root: use √ symbol (e.g. "√2" or "√(n)")
  - Multiplication: use × or · (e.g. "3 × 10⁸")
  - Greek letters: use Unicode: π θ α β γ λ μ Ω Δ
  - Comparisons: use ≤ ≥ ≠ ≈
  - Functions: write "log n", "sin θ", "cos x" as plain words, no backslashes
  - Infinity: use ∞
  - Arrows: use → ← ↔
  - Integrals/sums: describe in words (e.g. "the integral of sin(x) from 0 to π")

STRICT FORMAT REQUIREMENT:
Respond ONLY with a valid JSON array of objects, with NO markdown ticks, NO code blocks, NO commentary, NO preamble.
Each object in the array must follow this exact schema:
[
  {{
    "topic": "{topic}",
    "prompt": "Clear, concise question using plain text and Unicode math symbols",
    "option_a": "Option A text",
    "option_b": "Option B text",
    "option_c": "Option C text",
    "option_d": "Option D text",
    "correct_option_index": 0,
    "difficulty": "medium",
    "preview_coins": 10,
    "preview_xp": 20,
    "explanation": "Clear, educational explanation using plain text and Unicode math symbols."
  }}
]
Note: correct_option_index must be an integer from 0 to 3 (0=option_a, 1=option_b, 2=option_c, 3=option_d).
"""


# ── LaTeX-to-Unicode sanitizer ──────────────────────────────────────────────

import re as _re

_SUPERSCRIPT_MAP = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "n": "ⁿ", "i": "ⁱ", "x": "ˣ", "+": "⁺", "-": "⁻",
}

_SUBSCRIPT_MAP = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "n": "ₙ", "i": "ᵢ", "x": "ₓ",
}


def _to_superscript(s: str) -> str:
    return "".join(_SUPERSCRIPT_MAP.get(c, c) for c in s)


def _to_subscript(s: str) -> str:
    return "".join(_SUBSCRIPT_MAP.get(c, c) for c in s)


def sanitize_latex_to_unicode(text: str) -> str:
    """Convert any remaining LaTeX math notation in text to clean Unicode symbols."""
    if not text or not isinstance(text, str):
        return text

    # Strip enclosing dollar signs: $...$ or $$...$$
    text = _re.sub(r"\$\$([^\$]+)\$\$", r"\1", text)
    text = _re.sub(r"\$([^\$]+)\$", r"\1", text)

    # \left and \right delimiters
    text = _re.sub(r"\\left\s*\(", "(", text)
    text = _re.sub(r"\\right\s*\)", ")", text)
    text = _re.sub(r"\\left\s*\[", "[", text)
    text = _re.sub(r"\\right\s*\]", "]", text)
    text = _re.sub(r"\\left\s*\\?\{", "{", text)
    text = _re.sub(r"\\right\s*\\?\}", "}", text)
    text = _re.sub(r"\\left\s*\|", "|", text)
    text = _re.sub(r"\\right\s*\|", "|", text)

    # Fractions: \frac{a}{b} → (a/b)
    for _ in range(3):  # handle nested fracs
        text = _re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1/\2)", text)

    # Square root: \sqrt{x} → √(x), \sqrt[n]{x} → ⁿ√(x)
    text = _re.sub(r"\\sqrt\[(\d+)\]\{([^{}]+)\}", lambda m: _to_superscript(m.group(1)) + "√(" + m.group(2) + ")", text)
    text = _re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", text)

    # Greek letters
    _greek = {
        "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
        "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
        "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
        "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ", "chi": "χ",
        "psi": "ψ", "omega": "ω",
        "Alpha": "Α", "Beta": "Β", "Gamma": "Γ", "Delta": "Δ",
        "Theta": "Θ", "Lambda": "Λ", "Pi": "Π", "Sigma": "Σ",
        "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    }
    for name, symbol in _greek.items():
        text = _re.sub(rf"\\{name}\b", symbol, text)

    # Common math commands
    text = _re.sub(r"\\times\b", "×", text)
    text = _re.sub(r"\\cdot\b", "·", text)
    text = _re.sub(r"\\div\b", "÷", text)
    text = _re.sub(r"\\pm\b", "±", text)
    text = _re.sub(r"\\mp\b", "∓", text)
    text = _re.sub(r"\\infty\b", "∞", text)
    text = _re.sub(r"\\approx\b", "≈", text)
    text = _re.sub(r"\\neq\b", "≠", text)
    text = _re.sub(r"\\le\b|\\leq\b", "≤", text)
    text = _re.sub(r"\\ge\b|\\geq\b", "≥", text)
    text = _re.sub(r"\\rightarrow\b|\\to\b", "→", text)
    text = _re.sub(r"\\leftarrow\b", "←", text)
    text = _re.sub(r"\\leftrightarrow\b", "↔", text)
    text = _re.sub(r"\\degree\b", "°", text)

    # Function names (remove backslash but keep name)
    for fn in ["log", "ln", "sin", "cos", "tan", "cot", "sec", "csc",
               "arcsin", "arccos", "arctan", "lim", "max", "min", "sum", "prod"]:
        text = _re.sub(rf"\\{fn}\b", fn, text)

    # Subscripts: _{...} or _x
    text = _re.sub(r"_\{([^{}]+)\}", lambda m: _to_subscript(m.group(1)), text)
    text = _re.sub(r"_([0-9a-z])", lambda m: _to_subscript(m.group(1)), text)

    # Superscripts: ^{...} or ^x (do after subscripts to avoid conflicts)
    text = _re.sub(r"\^\{([^{}]+)\}", lambda m: _to_superscript(m.group(1)), text)
    text = _re.sub(r"\^([0-9a-z+\-])", lambda m: _to_superscript(m.group(1)), text)

    # Clean any remaining stray backslash-commands (e.g. \text{...})
    text = _re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = _re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    text = _re.sub(r"\\mathbf\{([^{}]+)\}", r"\1", text)

    # Clean stray curly braces left from LaTeX
    text = _re.sub(r"\{([^{}]*)\}", r"\1", text)

    return text.strip()


async def generate_ai_quiz_questions(topic: str = "STEM", num_questions: int = 10) -> list[dict]:
    """
    Generate multiple-choice quiz questions dynamically using Groq Cloud / configured AI provider.
    Ensures 10 fresh, unique questions changing every time.
    All text fields are sanitized to remove LaTeX and use proper Unicode math symbols.
    """
    import json
    import random
    import re
    import time

    seed = f"{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
    prompt = QUIZ_GEN_PROMPT_TEMPLATE.format(
        num_questions=min(num_questions, 15),
        topic=topic,
        seed=seed,
    )

    raw_response = await get_explanation(prompt)

    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    match = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            valid_questions = []
            for item in parsed:
                if (
                    "prompt" in item
                    and "option_a" in item
                    and "option_b" in item
                    and "option_c" in item
                    and "option_d" in item
                    and "correct_option_index" in item
                ):
                    valid_questions.append({
                        "topic": item.get("topic", topic),
                        "prompt": sanitize_latex_to_unicode(item["prompt"]),
                        "option_a": sanitize_latex_to_unicode(item["option_a"]),
                        "option_b": sanitize_latex_to_unicode(item["option_b"]),
                        "option_c": sanitize_latex_to_unicode(item["option_c"]),
                        "option_d": sanitize_latex_to_unicode(item["option_d"]),
                        "correct_option_index": int(item["correct_option_index"]) % 4,
                        "difficulty": item.get("difficulty", "medium"),
                        "preview_coins": int(item.get("preview_coins", 10)),
                        "preview_xp": int(item.get("preview_xp", 20)),
                        "explanation": sanitize_latex_to_unicode(
                            item.get("explanation", f"The correct answer is {item['option_a']}.")
                        ),
                    })
            if valid_questions:
                return valid_questions
    except Exception as exc:
        logger.warning("Failed to parse AI quiz JSON: %s. Raw: %s", exc, raw_response[:200])

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI generated an invalid question format. Please retry.",
    )

