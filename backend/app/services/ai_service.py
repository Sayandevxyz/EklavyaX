"""
app/services/ai_service.py
──────────────────────────
Synapse.ai – the AI explanation microservice engine.

Supports OpenRouter, Google Gemini, and OpenAI as interchangeable backends.
Prompt engineering ensures the AI acts as an empathetic tutor, NOT
a direct answer machine. All API calls are made via httpx.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Prompt Engineering ────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are Synapse, an expert, encouraging, and highly effective STEM AI tutor on the EklavyaX learning platform.

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


# ── Provider: OpenRouter ──────────────────────────────────────────────────────

# ── Fallback candidate models for OpenRouter free tier ────────────────────────
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
        "X-Title": "EklavyaX Synapse AI Tutor",
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


# ── Provider: Google Gemini ───────────────────────────────────────────────────

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


# ── Provider: OpenAI ─────────────────────────────────────────────────────────

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

    # Determine provider execution order
    provider_order = [provider]
    if provider != "openrouter" and settings.OPENROUTER_API_KEY:
        provider_order.append("openrouter")
    if provider != "gemini" and settings.GEMINI_API_KEY:
        provider_order.append("gemini")
    if provider != "openai" and settings.OPENAI_API_KEY:
        provider_order.append("openai")

    last_exception = None

    for p in provider_order:
        try:
            if p == "openrouter":
                return await _call_openrouter(prompt)
            elif p == "gemini":
                return await _call_gemini(prompt)
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

