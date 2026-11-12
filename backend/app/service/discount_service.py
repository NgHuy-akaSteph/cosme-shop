"""Discount service - logic ma giam gia.

NGUYEN TAC: chi server tinh tien giam. Client chi gui `code`, KHONG bao gio
gui `discount_amount` (neu khong user sua DevTools se giam gia khong gioi han).

Tinh tien giam o DAY - noi duy nhat. `order_service.create_order` goi
`compute_discount` va ghi ket qua vao `orders.discount_amount`.
"""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.coupon import Coupon


def normalize_code(code: str) -> str:
    """Chuan hoa ma coupon: bo khoang trang, viet hoa."""
    return code.strip().upper()


def compute_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    """
    Tinh so tien giam cho 1 coupon tren don co `subtotal`.

    Luon clamp trong [0, subtotal] => tong don khong bao gio am.
    Percent: bam tran `max_discount` neu co.
    Fixed: giam mot lan duy nhat, khong cong don voi percent.
    """
    if coupon.discount_type == "percent":
        amount = subtotal * Decimal(coupon.discount_value) / Decimal(100)
        if coupon.max_discount is not None:
            amount = min(amount, Decimal(coupon.max_discount))
    else:
        amount = Decimal(coupon.discount_value)

    # Lam tron ra so nguyen VND (khong co phan thap phan trong hoa don).
    amount = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(Decimal("0"), min(amount, subtotal))


def is_usable(coupon: Coupon, subtotal: Decimal) -> tuple[bool, str]:
    """
    Kiem tra coupon co dung duoc cho don nay khong.

    Returns:
        (ok, message) - message la ly do khi khong duoc dung.
    """
    if not coupon.is_active:
        return False, "Mã giảm giá đã ngừng hoạt động"

    if coupon.expires_at is not None:
        expires_at = coupon.expires_at
        # So sanh o aware datetime; DB trve timezone-aware (TIMESTAMPTZ).
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return False, "Mã giảm giá đã hết hạn"

    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        return False, "Mã giảm giá đã hết lượt sử dụng"

    if subtotal < Decimal(coupon.min_order_amount):
        return False, (
            f"Đơn hàng tối thiểu {coupon.min_order_amount:,} đ để dùng mã này"
        )

    return True, "OK"


async def get_coupon_by_code(db: AsyncSession, code: str) -> Coupon | None:
    """Lay coupon theo code (khong phan biet hoa/thuong)."""
    result = await db.execute(
        select(Coupon).where(Coupon.code == normalize_code(code))
    )
    return result.scalar_one_or_none()


async def validate_coupon(
    db: AsyncSession, code: str, subtotal: Decimal
) -> tuple[Coupon | None, Decimal, str]:
    """
    Kiem tra ma giam gia va tinh so tien giam (khong ghi DB).

    Dung cho endpoint preview o man checkout.

    Returns:
        (coupon, discount_amount, message)
        - coupon = None => khong dung duoc, message ly do.
        - coupon != None, discount_amount = 0 => ma hop le nhung giam 0
          (vd don 0 dong, hoac fixed > subtotal -> clamp ve 0).
    """
    coupon = await get_coupon_by_code(db, code)
    if coupon is None:
        return None, Decimal("0"), "Mã giảm giá không tồn tại"

    ok, message = is_usable(coupon, subtotal)
    if not ok:
        return None, Decimal("0"), message

    return coupon, compute_discount(coupon, subtotal), "OK"


async def consume_coupon(db: AsyncSession, coupon_id: int) -> bool:
    """
    Tang so lan dung cua coupon ATOMIC (chong race khi 2 nguoi dung cung ma).

    Dung `UPDATE ... WHERE used_count < max_uses ... RETURNING id` trong 1
    cau lenh => DB tu khoa row, khong co window "check roi increment".

    Returns:
        True neu tang thanh cong, False neu coupon da het luot.
    """
    result = await db.execute(
        update(Coupon)
        .where(Coupon.id == coupon_id)
        .where(
            (Coupon.max_uses.is_(None)) | (Coupon.used_count < Coupon.max_uses)
        )
        .where(
            (Coupon.expires_at.is_(None))
            | (Coupon.expires_at > datetime.now(timezone.utc))
        )
        .values(used_count=Coupon.used_count + 1)
        .returning(Coupon.id)
    )
    return result.scalar_one_or_none() is not None


async def get_coupon_by_id(db: AsyncSession, coupon_id: int) -> Coupon | None:
    """Lay coupon theo ID."""
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    return result.scalar_one_or_none()


async def get_all_coupons(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> list[Coupon]:
    """Lay danh sach coupon (Admin), moi nhat trong."""
    query = select(Coupon).order_by(Coupon.created_at.desc(), Coupon.id.desc())
    if is_active is not None:
        query = query.where(Coupon.is_active == is_active)
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_coupons_count(
    db: AsyncSession, is_active: bool | None = None
) -> int:
    """Dem so luong coupon (Admin)."""
    query = select(func.count(Coupon.id))
    if is_active is not None:
        query = query.where(Coupon.is_active == is_active)
    result = await db.execute(query)
    return result.scalar_one()


async def create_coupon(db: AsyncSession, **kwargs) -> Coupon:
    """
    Tao coupon moi (Admin).

    Raises:
        ValueError: code da ton tai.
    """
    code = normalize_code(kwargs.pop("code"))
    existing = await get_coupon_by_code(db, code)
    if existing is not None:
        raise ValueError("Mã giảm giá đã tồn tại")

    # Percent > 100 la khong hop le (giam nhieu hon gia tri don).
    if kwargs.get("discount_type") == "percent" and kwargs.get("discount_value", 0) > 100:
        raise ValueError("Phần trăm giảm không được vượt quá 100")

    coupon = Coupon(code=code, **kwargs)
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return coupon


async def update_coupon(db: AsyncSession, coupon_id: int, **kwargs) -> Coupon | None:
    """
    Cap nhat coupon (Admin).

    Chi set field co trong `kwargs` (API goi voi `exclude_unset=True`).
    Set `None` van co y nghia (VD `max_discount=None` = bo tran giam) nen
    KHONG bo qua gia tri None.
    """
    coupon = await get_coupon_by_id(db, coupon_id)
    if coupon is None:
        return None

    # Validate tren gia tri HIEU LUC (sau update), khong phai chi field gui len.
    # VD coupon dang "percent" 10%, admin chi doi `discount_value` = 150
    # -> phai bao loi chu khong phai bo qua vi `discount_type` khong doi.
    effective_type = kwargs.get("discount_type", coupon.discount_type)
    effective_value = kwargs.get("discount_value", coupon.discount_value)
    if effective_type == "percent" and effective_value > 100:
        raise ValueError("Phần trăm giảm không được vượt quá 100")

    for key, value in kwargs.items():
        if hasattr(coupon, key):
            setattr(coupon, key, value)

    await db.commit()
    await db.refresh(coupon)
    return coupon


async def delete_coupon(db: AsyncSession, coupon_id: int) -> bool:
    """
    Xoa coupon (Admin).

    Don da dung coupon van giu nguyen `discount_code` + `discount_amount`
    => lich su don khong bi anh huong.
    """
    coupon = await get_coupon_by_id(db, coupon_id)
    if coupon is None:
        return False

    await db.delete(coupon)
    await db.commit()
    return True
