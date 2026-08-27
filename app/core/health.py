from fastapi import APIRouter



router = APIRouter(
    tags=["Проверка, что приложение работает"]
)


@router.get("/health")
async def health_handler() -> dict:
    return {"status": "ok"}
