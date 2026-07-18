"""LLM client abstraction.

Supports OpenAI and OpenAI-compatible providers.
Uses structured output (function calling) to reduce hallucinations —
the model must conform to a JSON schema rather than generating free text.

Config via env vars: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL.
"""

import os
import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None
_model: Optional[str] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Configure in .env file.")
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


def get_model() -> str:
    global _model
    if _model is None:
        _model = os.getenv("OPENAI_MODEL", "gpt-4o")
    return _model


async def structured_completion(
    system_prompt: str,
    user_message: str,
    json_schema: dict,
    temperature: float = 0.2,
) -> dict:
    """Chat completion with structured JSON output via function calling.

    This is the primary mechanism for reducing hallucinations:
    the model must output data conforming to the provided JSON schema,
    rather than generating free-form text that may drift from the evidence.
    """
    client = get_client()
    model = get_model()

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=8192,
            tools=[{
                "type": "function",
                "function": {
                    "name": "output_result",
                    "description": "Output the structured analysis result",
                    "parameters": json_schema,
                }
            }],
            tool_choice={"type": "function", "function": {"name": "output_result"}},
        )

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            return json.loads(tool_calls[0].function.arguments)

        # Fallback
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM structured output: {e}")
        raise
    except Exception as e:
        logger.error(f"LLM structured completion failed: {e}")
        raise
