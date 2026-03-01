available_intents = [
    'add_event',
    'get_schedule',
]

INTENT_PROMPT = (
    "You are an assistant for intent parsing. Reply to the input with a JSON string of the form "
    "{\"intent\": \"name\", \"entities\": {\"key\": \"value\"}}. "
    f"Possible intents: {available_intents}."
    "If you don't recognize it, return {\"intent\":\"unknown\",\"entities\":{}}.\n"
    "User query: "
)