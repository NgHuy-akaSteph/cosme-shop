"""AI API endpoints - proxy sang AI service noi bo"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.service import ai_service, product_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


class QuizInput(BaseModel):
    """Quiz input tu user."""
    skin_type: str = Field(..., pattern="^(oily|dry|combination|sensitive|normal)$")
    concerns: list[str]
    budget: float = Field(..., gt=0)
    age: int | None = None
    allergies: list[str] = []


class RoutineBuilderRequest(BaseModel):
    """Request cho routine builder."""
    quiz: QuizInput


@router.post("/routine")
async def build_routine(
    request: RoutineBuilderRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo skincare routine tu quiz (Public).
    
    - **quiz**: Thong tin quiz cua nguoi dung
      - **skin_type**: Loai da (oily, dry, combination, sensitive, normal)
      - **concerns**: Van de da (acne, dark_spots, wrinkles, dullness, dehydration, redness, pores, aging)
      - **budget**: Tong ngan sach VND
      - **age**: Tuoi (optional)
      - **allergies**: Di ung voi (optional)
    """
    # Filter products based on quiz
    quiz = request.quiz
    
    # Build filter params
    skin_types = [quiz.skin_type]
    
    # Get products matching skin type and concerns
    # Cot skin_types/du lieu luu duoi dang JSONB ho tro JSONB @> contains.
    # Neu query that bai (vi du: migration chua apply), fallback ve loc trong Python.
    try:
        products, _ = await product_service.get_products(
            db,
            skip=0,
            limit=50,
            skin_types=skin_types,
            is_active=True,
        )
    except Exception as exc:
        print(f"AI routine: product query failed ({exc}), using Python fallback")
        await db.rollback()
        all_products, _ = await product_service.get_products(
            db,
            skip=0,
            limit=50,
            is_active=True,
        )
        products = [
            p for p in all_products
            if p.skin_types and quiz.skin_type in p.skin_types
        ]
    
    # Filter products by price (max budget/4 per product for 4 steps)
    max_price_per_product = quiz.budget / 4
    filtered_products = []
    
    for p in products:
        effective_price = float(p.sale_price if p.sale_price else p.price)
        if effective_price <= max_price_per_product:
            # Check allergies
            if quiz.allergies and p.free_from:
                has_allergy = any(
                    allergy.lower() in [a.lower() for a in p.free_from]
                    for allergy in quiz.allergies
                )
                if has_allergy:
                    continue
            
            filtered_products.append({
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "category": p.category.name if p.category else None,
                "brand": p.brand.name if p.brand else None,
                "skin_types": p.skin_types,
                "concerns": p.concerns,
                "key_ingredients": p.key_ingredients,
                "free_from": p.free_from,
                "usage_time": p.usage_time,
                "step": p.step,
            })
    
    if not filtered_products:
        return {
            "data": {
                "steps": [],
                "note": "Không tìm thấy sản phẩm phù hợp với ngân sách của bạn. Hãy thử tăng ngân sách."
            },
            "message": "OK",
        }
    
    # Call AI service
    try:
        quiz_dict = {
            "skin_type": quiz.skin_type,
            "concerns": quiz.concerns,
            "budget": quiz.budget,
            "age": quiz.age,
            "allergies": quiz.allergies,
        }
        
        result = await ai_service.call_routine_builder(quiz_dict, filtered_products)
        
        return {
            "data": result,
            "message": "OK",
        }
    except ai_service.AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": str(e), "code": "AI_SERVICE_ERROR"},
        )
