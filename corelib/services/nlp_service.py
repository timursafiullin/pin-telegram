import json

from corelib.services.llm_service import LLMService
from corelib.utils.prompts import (
    INTENT_PROMPT,
)

class NLPService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def parse_intent(self, user_message: str) -> dict:
        system_prompt = INTENT_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        raw_json = await self.llm.chat_completion(messages, temperature=0.0)

        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return {"intent": "unknown", "entities": {}}