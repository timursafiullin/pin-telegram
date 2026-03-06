import httpx
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


router = Router()


@router.message(Command("create_invite_code"))
async def create_invite_code_command(message: Message):
    telegram_id = str(message.from_user.id)
    payload = {
        "telegram_id": telegram_id,
        "role": "user",
        "max_uses": 1,
        "expires_in_days": 3,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/invites/create", json=payload)

    if response.status_code >= 400:
        await message.answer("Invite code creation is available only for owner users.")
        return

    data = response.json()
    await message.answer(
        "Invite created:\n"
        f"code: <code>{data['code']}</code>\n"
        f"role: {data['role']}\n"
        f"max_uses: {data['max_uses']}\n"
        f"expires_at: {data['expires_at']}"
    )


@router.message(Command("my_invite_codes"))
async def my_invite_codes_command(message: Message):
    telegram_id = str(message.from_user.id)

    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/bot/invites/my", params={"telegram_id": telegram_id})

    if response.status_code >= 400:
        await message.answer("Unable to load invite codes. Ensure you are registered.")
        return

    items = response.json().get("items", [])
    if not items:
        await message.answer("You have no invite codes yet.")
        return

    lines = []
    for invite in items:
        lines.append(
            f"<code>{invite['code']}</code> | role={invite['role']} | "
            f"uses={invite['uses_count']}/{invite['max_uses'] if invite['max_uses'] is not None else '∞'} | "
            f"active={invite['is_active']}"
        )
    await message.answer("Your invite codes:\n" + "\n".join(lines))
