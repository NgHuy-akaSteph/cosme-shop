"""Brand API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin
from app.model.user import User
from app.schemas.brand import BrandCreate, BrandUpdate, BrandResponse, BrandListResponse
from app.service import brand_service

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("", response_model=BrandListResponse)
async def list_brands(
    page: int = 1,
    size: int = 100,
    sort: str | None = Query(None, description="newest | oldest | name_asc"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach thuong hieu (Public).

    `sort`: `newest` (moi tao truoc), `oldest`, mac dinh alphabet theo ten.
    """
    skip = (page - 1) * size
    brands = await brand_service.get_all_brands(db, skip=skip, limit=size, sort=sort)
    total = await brand_service.get_brands_count(db)
    
    return BrandListResponse(
        data=[
            BrandResponse(
                id=b.id,
                name=b.name,
                slug=b.slug,
                description=b.description,
                logo_url=b.logo_url,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in brands
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{brand_id}", response_model=dict)
async def get_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet thuong hieu (Public).
    """
    brand = await brand_service.get_brand_by_id(db, brand_id)
    
    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy thương hiệu", "code": "NOT_FOUND"},
        )
    
    return {
        "data": {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "description": brand.description,
            "logo_url": brand.logo_url,
            "created_at": brand.created_at,
        },
        "message": "OK",
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_brand(
    data: BrandCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Tao thuong hieu moi (Admin).
    """
    try:
        brand = await brand_service.create_brand(
            db,
            name=data.name,
            slug=data.slug,
            description=data.description,
            logo_url=data.logo_url,
        )
        
        return {
            "data": {
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "description": brand.description,
                "logo_url": brand.logo_url,
                "created_at": brand.created_at,
            },
            "message": "Tạo thương hiệu thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.patch("/{brand_id}", response_model=dict)
async def update_brand(
    brand_id: int,
    data: BrandUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Cap nhat thuong hieu (Admin).
    """
    try:
        update_data = data.model_dump(exclude_unset=True)
        brand = await brand_service.update_brand(db, brand_id, **update_data)
        
        if brand is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy thương hiệu", "code": "NOT_FOUND"},
            )
        
        return {
            "data": {
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "description": brand.description,
                "logo_url": brand.logo_url,
                "updated_at": brand.updated_at,
            },
            "message": "Cập nhật thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Xoa thuong hieu (Admin).
    """
    success = await brand_service.delete_brand(db, brand_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy thương hiệu", "code": "NOT_FOUND"},
        )
