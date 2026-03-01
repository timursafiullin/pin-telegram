import json
import logging
from datetime import datetime

from corelib.services.llm_service import LLMService
from corelib.utils.prompts import INTENT_PROMPT_TEMPLATE, available_intents

logger = logging.getLogger("corelib.nlp")

class NLPService:
    def __init__(self, llm: LLMService):
        self.llm = llm

    async def parse_intent(self, user_message: str) -> dict:
        system_prompt = INTENT_PROMPT_TEMPLATE.format(
            available_intents=", ".join(available_intents),
            today_date=datetime.utcnow().date().isoformat(),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        raw_json = await self.llm.chat_completion(messages, temperature=0.0)
        logger.info("intent llm raw response=%s", raw_json, extra={"log_prefix": "[NLP]"})

        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("intent llm response is not valid JSON raw=%s", raw_json, extra={"log_prefix": "[NLP]"})
            return {"intent": "unknown", "entities": {}}

    async def parse_intent_list(self, user_message: str) -> list[dict]:
        parsed = await self.parse_intent(user_message)
        if isinstance(parsed, list):
            return parsed
        return [parsed]
