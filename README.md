# Project
**Personal Intelligence Node (PIN)** – an AI assistant for personal digital infrastructure, designed to scale into a multi-user platform within a closed local network. This repository provides an example of a Telegram bot interface for interacting with the assistant.

# Start

First, ensure you have **Python 3.12.x** installed. Then, create a virtual environment and install the required dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r ./requirements.txt 
```

Before proceeding, **make sure** your database is active and you've created your own `.env` file with all the necessary variables.

Then, run the **FastAPI app**:
```bash
fastapi dev ./apps/api/main.py
```

Now you're ready to start the **Telegram bot**:
```bash
python3.12 ./apps/telegram_bot/start_bot.py
```