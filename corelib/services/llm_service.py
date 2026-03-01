import httpx
from corelib.config import Settings

class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.0
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.LLM_API_URL}/{self.settings.LLM_MODEL}",
                headers={"Authorization": f"Bearer {self.settings.LLM_API_KEY}"},
                json={
                    "model": self.settings.LLM_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
