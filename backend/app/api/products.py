"""Product API endpoints"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin
from app.model.user import User
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
)
from app.service import product_service
from app.service import product_stock

router = APIRouter(prefix="/api/products", tags=["products"])


def _product_to_dict(p) -> dict[str, Any]:
    """Convert product model to dict."""
    from app.core.cloudinary import build_image_urls

    # Lay URL anh chinh (anh dau tien hoac anh is_main=true)
    main_image_url: str | None = None
    main_image: dict[str, Any] | None = None
    if p.images_rel:
        sorted_images = sorted(p.images_rel, key=lambda img: (not img.is_main, img.position))
        if sorted_images:
            main_image = sorted_images[0]
            main_image_url = main_image.secure_url

    def _iso(v):
        """Convert datetime to ISO string; pass through if already str/None."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        return v.isoformat()

    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "price": str(p.price),
        "sale_price": str(p.sale_price) if p.sale_price else None,
        # Stock hien thi: san pham co bien the -> tong stock variants
        # (gia tri dan xuat, xem service/product_stock.py)
        "stock": product_stock.effective_stock(p),
        # Synthesized for client convenience (frontend expects image_url field)
        "image_url": main_image_url,
        # URL bien the theo kich co hien thi (sinh tu public_id qua Cloudinary)
        "image_urls": (
            build_image_urls(main_image.public_id) if main_image else None
        ),
        "category_id": p.category_id,
        "brand_id": p.brand_id,
        "skin_types": p.skin_types,
        "concerns": p.concerns,
        "key_ingredients": p.key_ingredients,
        "free_from": p.free_from,
        "variants": p.variants,
        "sold_count": p.sold_count,
        "rating_avg": float(p.rating_avg) if p.rating_avg else 0,
        "rating_count": p.rating_count,
        "is_active": p.is_active,
        "created_at": _iso(p.created_at),
        "updated_at": _iso(p.updated_at),
        "category": {
            "id": p.category.id,
            "name": p.category.name,
            "slug": p.category.slug,
        } if p.category else None,
        "brand": {
            "id": p.brand.id,
            "name": p.brand.name,
            "slug": p.brand.slug,
        } if p.brand else None,
        # Danh sach anh Cloudinary (empty list neu chua co)
        "images": [
            {
                "id": img.id,
                "product_id": img.product_id,
                "public_id": img.public_id,
                "secure_url": img.secure_url,
                "alt_text": img.alt_text,
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "position": img.position,
                "is_main": img.is_main,
                "image_urls": build_image_urls(img.public_id),
                "created_at": _iso(img.created_at),
                "updated_at": _iso(img.updated_at),
            }
            for img in (p.images_rel or [])
        ],
    }


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    brand_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    skin_types: str | None = None,  # comma-separated
    concerns: str | None = None,  # comma-separated
    search: str | None = None,
    sort: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach san pham (Public).
    Co filter va sort.
    """
    # Parse comma-separated lists
    skin_types_list = skin_types.split(",") if skin_types else None
    concerns_list = concerns.split(",") if concerns else None
    
    skip = (page - 1) * size
    products, total = await product_service.get_products(
        db,
        skip=skip,
        limit=size,
        category_id=category_id,
        brand_id=brand_id,
        min_price=min_price,
        max_price=max_price,
        skin_types=skin_types_list,
        concerns=concerns_list,
        search=search,
        sort=sort,
    )
    
    return ProductListResponse(
        data=[_product_to_dict(p) for p in products],
        total=total,
        page=page,
        size=size,
    )


@router.get("/best-sellers", response_model=ProductListResponse)
async def get_best_sellers(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay san pham ban chay (Public).
    """
    products = await product_service.get_best_sellers(db, limit=limit)
    
    return ProductListResponse(
        data=[_product_to_dict(p) for p in products],
        total=len(products),
        page=1,
        size=limit,
    )


@router.get("/{product_id}", response_model=dict)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet san pham (Public).
    """
    product = await product_service.get_product_by_id(db, product_id)
    
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy sản phẩm", "code": "NOT_FOUND"},
        )
    
    return {
        "data": _product_to_dict(product),
        "message": "OK",
    }


@router.get("/{product_id}/similar", response_model=ProductListResponse)
async def get_similar_products(
    product_id: int,
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay san pham tuong tu (Public).
    """
    products = await product_service.get_similar_products(db, product_id, limit=limit)
    
    return ProductListResponse(
        data=[_product_to_dict(p) for p in products],
        total=len(products),
        page=1,
        size=limit,
    )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Tao san pham moi (Admin).
    """
    try:
        product = await product_service.create_product(
            db,
            name=data.name,
            price=data.price,
            category_id=data.category_id,
            brand_id=data.brand_id,
            slug=data.slug,
            description=data.description,
            sale_price=data.sale_price,
            stock=data.stock,
            skin_types=data.skin_types,
            concerns=data.concerns,
            key_ingredients=data.key_ingredients,
            free_from=data.free_from,
            variants=data.variants,
        )
        
        return {
            "data": _product_to_dict(product),
            "message": "Tạo sản phẩm thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.patch("/{product_id}", response_model=dict)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Cap nhat san pham (Admin).
    """
    try:
        update_data = data.model_dump(exclude_unset=True)
        product = await product_service.update_product(db, product_id, **update_data)
        
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy sản phẩm", "code": "NOT_FOUND"},
            )
        
        return {
            "data": _product_to_dict(product),
            "message": "Cập nhật thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Xoa san pham (Admin - soft delete).
    """
    success = await product_service.delete_product(db, product_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy sản phẩm", "code": "NOT_FOUND"},
        )
