"""Logic stock san pham - 1 nguon su that duy nhat.

Quy tac:
- San pham **khong co variants**: `products.stock` la nguon su that.
- San pham **co variants**: `variants[i].stock` la nguon su that; `products.stock`
  duoc **tinh lai** = tong stock cua cac variants (gia tri dan xuat).

Ly do: truoc day order service tru ca `variants[i].stock` **va** `products.stock`.
Hai nguon doc lap -> admin nhap tay lech nhau (vd product.stock = 0 nhung variants
con hang) se hien "Het hang" tren danh sach san pham.
"""

from typing import Any


def has_variants(product) -> bool:
    """San pham co bien the hay khong."""
    return bool(getattr(product, "variants", None))


def find_variant(product, variant_id: str) -> dict[str, Any] | None:
    """Tim bien the theo `id` trong product. Tra `None` neu khong co."""
    for variant in getattr(product, "variants", None) or []:
        if variant.get("id") == variant_id:
            return variant
    return None


def variant_stock(variant: dict[str, Any]) -> int:
    """Stock cua 1 bien the (null -> 0)."""
    try:
        return int(variant.get("stock") or 0)
    except (TypeError, ValueError):
        return 0


def total_variant_stock(product) -> int:
    """Tong stock cua tat ca bien the cua product."""
    variants = getattr(product, "variants", None) or []
    return sum(variant_stock(v) for v in variants)


def recompute_stock(product) -> int:
    """
    Dong bo `products.stock` voi tong stock cua variants.

    - Co variants -> gan `product.stock` = tong stock variants.
    - Khong co variants -> giu nguyen `product.stock` (nguon su that cua no).

    Returns:
        Gia tri stock hien tai cua product.
    """
    if has_variants(product):
        product.stock = total_variant_stock(product)
    return product.stock


def effective_stock(product) -> int:
    """
    Stock nguoi dung nhin thay tren FE.

    - Co variants -> tong stock variants (khong phai `product.stock` co the cu).
    - Khong co variants -> `product.stock`.
    """
    if has_variants(product):
        return total_variant_stock(product)
    return int(getattr(product, "stock", 0) or 0)
