"""Category API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin
from app.model.user import User
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse
)
from app.service import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    page: int = 1,
    size: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach danh muc (Public).
    """
    skip = (page - 1) * size
    categories = await category_service.get_all_categories(db, skip=skip, limit=size)
    total = await category_service.get_categories_count(db)
    
    return CategoryListResponse(
        data=[
            CategoryResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                image_url=c.image_url,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in categories
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{category_id}", response_model=dict)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet danh muc (Public).
    """
    category = await category_service.get_category_by_id(db, category_id)
    
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy danh mục", "code": "NOT_FOUND"},
        )
    
    return {
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "created_at": category.created_at,
        },
        "message": "OK",
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Tao danh muc moi (Admin).
    """
    try:
        category = await category_service.create_category(
            db,
            name=data.name,
            slug=data.slug,
            description=data.description,
            image_url=data.image_url,
        )
        
        return {
            "data": {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "image_url": category.image_url,
                "created_at": category.created_at,
            },
            "message": "Tạo danh mục thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.patch("/{category_id}", response_model=dict)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Cap nhat danh muc (Admin).
    """
    try:
        update_data = data.model_dump(exclude_unset=True)
        category = await category_service.update_category(db, category_id, **update_data)
        
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy danh mục", "code": "NOT_FOUND"},
            )
        
        return {
            "data": {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "image_url": category.image_url,
                "updated_at": category.updated_at,
            },
            "message": "Cập nhật thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Xoa danh muc (Admin).
    """
    success = await category_service.delete_category(db, category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy danh mục", "code": "NOT_FOUND"},
        )
