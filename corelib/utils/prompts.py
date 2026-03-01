available_intents = [
    'add_event',
    'get_schedule',
    'create_invite_code',
    'list_my_invite_codes',
]

INTENT_PROMPT = (
    "You are an assistant for intent parsing. Reply to the input with a JSON string of the form "
    "{\"intent\": \"name\", \"entities\": {\"key\": \"value\"}}. "
    f"Possible intents: {available_intents}."
    "For create_invite_code intent, extract entities role (owner|tester|user), max_uses (int), expires_in_days (int)."
    "If you don't recognize it, return {\"intent\":\"unknown\",\"entities\":{}}.\n"
    "User query: "
)
