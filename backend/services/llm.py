import base64
import os
from typing import List, Optional

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def chat_text(messages: List[dict]) -> str:
    # messages: [{role: 'user'|'assistant'|'system', content: '...'}]
    # Gọi model bạn chọn. Ví dụ OpenAI Responses:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

async def chat_vision(user_prompt: str, image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    }
                ],
            }
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
