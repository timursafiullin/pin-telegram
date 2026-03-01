from fastapi import APIRouter, Depends, HTTPException
from dateutil import parser
from pydantic import BaseModel

from corelib.services import (
    NLPService,
    ScheduleService,
    LLMService,
)
from apps.api.deps import (
    get_nlp_service,
    get_schedule_service,
    get_llm_service,
    get_user
)

router = APIRouter()

class BotMessage(BaseModel):
    user_id: str
    text: str

@router.post("/message")
async def handle_bot_message(
    payload: BotMessage,
    nlp_service: NLPService = Depends(get_nlp_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    user = await get_user(payload.user_id)
    parsed = await nlp_service.parse_intent_list(payload.text)

    result = list()
    for p in parsed:
        intent = p.get("intent")
        entities = p.get("entities", {})
        if intent == "add_event":
            dt = parser.parse(f"{entities['date']} {entities['time']}").astimezone(user.timezone)
            created_event = await schedule_service.create_event(
                user_id=user.id,
                title=p["title"],
                start_time=dt,
                location=p.get("location"),
                recurrence=p.get("recurrence"),
                remind_before_minutes=p.get("remind_before_minutes", 60),
            )
            result.append({"event": {"title": created_event.title, "start_time": created_event.start_time.isoformat()}})
        elif intent == "get_schedule":
            events = await schedule_service.get_upcoming_events(user.id, entities["date"])
            result.append({"events": [ {"title": e.title, "start_time": e.start_time.isoformat()} for e in events ]})
        else:
            result.append({"info": "Sorry, I did not understand the request."})

    answer = await llm_service.chat_completion(
        [
            {"role":"system","content":"You are a personal assistant. Respond in a friendly and concise manner."},
            {"role":"user","content":f"Data: {result}. Generate a response."},
        ],
        temperature=0.3,
    )
    return {"reply": answer}