"""Helper sap xep danh sach dung chung cho cac bang co cot `name`.

Moi bang admin (categories, brands, ...) can mot quy tac sap xep giong nhau
de danh sach khong "lon xon". Quy tac mac dinh giu nguyen hanh vi cu (alphabet
theo `name`) cho public API; trang admin truyen `sort=newest` de lay ban ghi
moi nhat truoc.

Moi `order_by` deu co tiebreak theo `id` de phan trang on dinh: `created_at`
duoc sinh tu `now()` theo transaction nen nhieu ban ghi co the trung timestamp
- thieu tiebreak se lam record lap/bo qua giua cac trang.
"""

from typing import Any, TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import DeclarativeBase

# Gia tri hop le cua query param `sort`.
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_NAME_ASC = "name_asc"

# Model co `name`, `created_at`, `id`.
ModelT = TypeVar("ModelT", bound=DeclarativeBase)


def apply_sort(query: Select[Any], model: type[ModelT], sort: str | None) -> Select[Any]:
    """
    Ap dung quy tac sap xep cho query danh sach.

    Args:
        query: Query base (chua `order_by`).
        model: Model SQLAlchemy (can co `name`, `created_at`, `id`).
        sort: Gia tri sort. `newest` / `oldest` / `name_asc`.
            Khong truyen hoac gia tri la -> `name_asc` (mac dinh).

    Returns:
        Query da co `order_by`.
    """
    if sort == SORT_NEWEST:
        return query.order_by(model.created_at.desc(), model.id.desc())
    if sort == SORT_OLDEST:
        return query.order_by(model.created_at.asc(), model.id.asc())
    # Mac dinh: alphabet theo ten + tiebreak id (giữ hành vi public cũ).
    return query.order_by(model.name.asc(), model.id.asc())
