from fastapi import APIRouter

router = APIRouter()


@router.get('/health')
async def users_health():
    return {'status': 'ok'}
