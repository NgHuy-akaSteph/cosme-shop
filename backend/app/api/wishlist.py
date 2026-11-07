"""Wishlist API endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.model.user import User
from app.schemas.wishlist import WishlistResponse
from app.service import wishlist_service
from app.service import product_stock

router = APIRouter(prefix="/api/wishlist", tags=["wishlist"])


def _product_to_dict(p) -> dict[str, Any]:
    """Convert product to dict for wishlist."""
    from app.core.cloudinary import build_image_urls

    main_image_url: str | None = None
    main_image_urls: dict[str, str] | None = None
    if p.images_rel:
        sorted_images = sorted(p.images_rel, key=lambda img: (not img.is_main, img.position))
        if sorted_images:
            main_image_url = sorted_images[0].secure_url
            main_image_urls = build_image_urls(sorted_images[0].public_id)

    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "price": str(p.price),
        "sale_price": str(p.sale_price) if p.sale_price else None,
        "stock": product_stock.effective_stock(p),
        "image_url": main_image_url,
        "image_urls": main_image_urls,
    }


@router.get("", response_model=WishlistResponse)
async def get_my_wishlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach san pham yeu thich (User).
    """
    wishlist = await wishlist_service.get_user_wishlist(db, current_user.id)
    
    return WishlistResponse(
        data=[
            {
                "id": w.id,
                "product_id": w.product_id,
                "created_at": w.created_at,
                "product": _product_to_dict(w.product) if w.product else None,
            }
            for w in wishlist
        ],
        message="OK",
    )


@router.post("/{product_id}", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Them san pham vao wishlist (User).
    """
    try:
        wishlist = await wishlist_service.add_to_wishlist(
            db, current_user.id, product_id
        )
        
        return {
            "data": {
                "id": wishlist.id,
                "product_id": wishlist.product_id,
                "created_at": wishlist.created_at,
            },
            "message": "Thêm vào wishlist thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Xoa san pham khoi wishlist (User).
    """
    success = await wishlist_service.remove_from_wishlist(
        db, current_user.id, product_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Sản phẩm không có trong wishlist", "code": "NOT_FOUND"},
        )
