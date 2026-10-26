from app.api.dto import Category
from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories() -> list[Category]:
    return list(Category)
