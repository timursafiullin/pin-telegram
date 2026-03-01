from fastapi import FastAPI, Depends
from apps.api.routers import bot, users, events

def create_app() -> FastAPI:
    app = FastAPI(title="Personal Intelligence Node API")
    app.include_router(bot.router, prefix="/bot")
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(events.router, prefix="/events", tags=["events"])
    return app

app = create_app()