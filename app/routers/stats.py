"""Usage statistics for the calling API key."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.database import get_db
from app.models import ApiKey, ValidationLog
from app.schemas import DailyStats, StatsResponse, TypeStats

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(api_key: ApiKey = Depends(require_api_key), db: Session = Depends(get_db)):
    """Counts for this API key: per ID type, and per day with a running total."""
    mine = ValidationLog.api_key_id == api_key.id

    # SELECT id_type, COUNT(*), SUM(CASE WHEN is_valid THEN 1 ELSE 0 END)
    # FROM validation_logs WHERE api_key_id = :id GROUP BY id_type
    by_type_rows = db.execute(
        select(
            ValidationLog.id_type,
            func.count().label("total"),
            func.sum(case((ValidationLog.is_valid, 1), else_=0)).label("valid"),
        )
        .where(mine)
        .group_by(ValidationLog.id_type)
        .order_by(ValidationLog.id_type)
    ).all()

    # SELECT DATE(created_at) AS day, COUNT(*),
    #        SUM(COUNT(*)) OVER (ORDER BY DATE(created_at))
    # FROM validation_logs WHERE api_key_id = :id GROUP BY day
    #
    # GROUP BY makes one row per day. The window function then adds up
    # those daily counts from the first day to the current row.
    day = func.date(ValidationLog.created_at)
    daily_rows = db.execute(
        select(
            day.label("day"),
            func.count().label("requests"),
            func.sum(func.count()).over(order_by=day).label("running_total"),
        )
        .where(mine)
        .group_by(day)
        .order_by(day)
    ).all()

    by_type = [
        TypeStats(id_type=row.id_type, total=row.total, valid=row.valid, invalid=row.total - row.valid)
        for row in by_type_rows
    ]
    daily = [
        DailyStats(day=str(row.day), requests=row.requests, running_total=row.running_total)
        for row in daily_rows
    ]
    return StatsResponse(
        total_validations=sum(item.total for item in by_type),
        by_type=by_type,
        daily=daily,
    )
