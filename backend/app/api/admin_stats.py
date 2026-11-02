"""Admin API - thong ke dashboard"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.model.user import User
from app.service.stats_service import get_dashboard_stats

router = APIRouter(prefix="/api/admin/stats", tags=["admin-stats"])


@router.get("", response_model=dict)
async def dashboard_stats(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lay tong hop so lieu cho dashboard admin."""
    stats = await get_dashboard_stats(db)
    return {"data": stats, "message": "OK"}
