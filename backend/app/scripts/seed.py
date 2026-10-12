"""Seed script - Tao du lieu mau cho database"""

import asyncio
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import AsyncSessionLocal
from app.model.user import User
from app.model.category import Category
from app.model.brand import Brand
from app.model.product import Product
from app.model.product_image import ProductImage
from app.core.security import hash_password


def _make_public_id(url: str, slug: str) -> str:
    """Tao public_id determinstic nhung unique per product (slug + url hash)."""
    return "seed_" + hashlib.md5(f"{slug}|{url}".encode("utf-8")).hexdigest()[:16]


async def seed_database():
    """Tao du lieu mau."""
    print("Starting seed...")
    
    async with AsyncSessionLocal() as db:
        # 1. Create admin user
        admin = User(
            email="admin@cosme-shop.com",
            password_hash=hash_password("admin123"),
            full_name="Quản Trị Viên",
            phone="0900000000",
            address="Hà Nội, Việt Nam",
            role="admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        print("Created admin user")

        # 2. Create test user
        test_user = User(
            email="user@cosme-shop.com",
            password_hash=hash_password("user123"),
            full_name="Người Dùng Test",
            phone="0900123456",
            address="TP. Hồ Chí Minh, Việt Nam",
            role="user",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(test_user)
        print("Created test user")
        
        await db.flush()  # Get IDs
        
        # 3. Create categories
        categories_data = [
            {"name": "Skincare", "slug": "skincare", "description": "Chăm sóc da mặt", "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400"},
            {"name": "Makeup", "slug": "makeup", "description": "Trang điểm", "image_url": "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=400"},
            {"name": "Sunscreen", "slug": "sunscreen", "description": "Kem chống nắng", "image_url": "https://images.unsplash.com/photo-1556227834-09f1de7a7d14?w=400"},
            {"name": "Cleanser", "slug": "cleanser", "description": "Sữa rửa mặt", "image_url": "https://images.unsplash.com/photo-1557750255-c76072a7aad1?w=400"},
            {"name": "Serum", "slug": "serum", "description": "Tinh chất dưỡng da", "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400"},
            {"name": "Toner", "slug": "toner", "description": "Nước cân bằng da", "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400"},
            {"name": "Moisturizer", "slug": "moisturizer", "description": "Kem dưỡng ẩm", "image_url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400"},
            {"name": "Mask", "slug": "mask", "description": "Mặt nạ", "image_url": "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=400"},
        ]
        
        categories = []
        for cat_data in categories_data:
            cat = Category(
                **cat_data,
                created_at=datetime.now(timezone.utc),
            )
            db.add(cat)
            categories.append(cat)
        print(f"Created {len(categories)} categories")
        
        await db.flush()
        
        # 4. Create brands
        brands_data = [
            {"name": "The Ordinary", "slug": "the-ordinary", "description": "Dược mỹ phẩm hiệu quả với giá hợp lý", "logo_url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200"},
            {"name": "La Roche-Posay", "slug": "la-roche-posay", "description": "Dược mỹ phẩm Pháp chuyên về da nhạy cảm", "logo_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=200"},
            {"name": "Cocoon", "slug": "cocoon", "description": "Thương hiệu mỹ phẩm Việt Nam", "logo_url": "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=200"},
            {"name": "Innisfree", "slug": "innisfree", "description": "Mỹ phẩm Hàn Quốc từ thiên nhiên", "logo_url": "https://images.unsplash.com/photo-1556227834-09f1de7a7d14?w=200"},
            {"name": "Klairs", "slug": "klairs", "description": "Mỹ phẩm Hàn Quốc dịu nhẹ", "logo_url": "https://images.unsplash.com/photo-1557750255-c76072a7aad1?w=200"},
        ]
        
        brands = []
        for brand_data in brands_data:
            brand = Brand(
                **brand_data,
                created_at=datetime.now(timezone.utc),
            )
            db.add(brand)
            brands.append(brand)
        print(f"Created {len(brands)} brands")
        
        await db.flush()
        
        # 5. Create products
        products_data = [
            # Skincare products
            {
                "name": "Niacinamide 10% + Zinc 1%",
                "slug": "the-ordinary-niacinamide-10-zinc-1",
                "description": "Giảm bít tắc lỗ chân lông, kiểm soát dầu thừa, cải thiện tone da",
                "price": Decimal("180000"),
                "stock": 50,
                "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
                "category_id": categories[0].id,  # Skincare
                "brand_id": brands[0].id,  # The Ordinary
                "skin_types": ["oily", "combination"],
                "concerns": ["pores", "dullness"],
                "key_ingredients": ["niacinamide", "zinc"],
                "free_from": ["alcohol", "fragrance"],
                "variants": None,
                "sold_count": 120,
                "rating_avg": Decimal("4.5"),
                "rating_count": 89,
            },
            {
                "name": "Glycolic Acid 7% Toning Solution",
                "slug": "the-ordinary-glycolic-acid-7",
                "description": "Tẩy tế bào chết hóa học, làm sáng da, cải thiện kết cấu",
                "price": Decimal("245000"),
                "stock": 35,
                "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
                "category_id": categories[5].id,  # Toner
                "brand_id": brands[0].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dullness", "dark_spots"],
                "key_ingredients": ["glycolic_acid"],
                "free_from": ["alcohol", "fragrance"],
                "variants": None,
                "sold_count": 95,
                "rating_avg": Decimal("4.3"),
                "rating_count": 67,
            },
            {
                "name": "Effaclar Gel Nettoyant",
                "slug": "la-roche-posay-effaclar-gel",
                "description": "Sữa rửa mặt dịu nhẹ cho da dầu, mụn",
                "price": Decimal("320000"),
                "stock": 40,
                "image_url": "https://images.unsplash.com/photo-1557750255-c76072a7aad1?w=400",
                "category_id": categories[3].id,  # Cleanser
                "brand_id": brands[1].id,  # La Roche-Posay
                "skin_types": ["oily", "combination", "sensitive"],
                "concerns": ["acne"],
                "key_ingredients": ["thermal_water", "zinc"],
                "free_from": ["soap", "alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 150,
                "rating_avg": Decimal("4.6"),
                "rating_count": 112,
            },
            {
                "name": "Anthelios Fluid SPF 50+",
                "slug": "la-roche-posay-anthelios-fluid-spf50",
                "description": "Kem chống nắng không nhờn rít, phù hợp da dầu",
                "price": Decimal("520000"),
                "stock": 25,
                "image_url": "https://images.unsplash.com/photo-1556227834-09f1de7a7d14?w=400",
                "category_id": categories[2].id,  # Sunscreen
                "brand_id": brands[1].id,
                "skin_types": ["oily", "combination", "sensitive"],
                "concerns": ["acne", "aging"],
                "key_ingredients": ["thermal_water", "niacinamide"],
                "free_from": ["fragrance", "parabens"],
                "variants": None,
                "sold_count": 200,
                "rating_avg": Decimal("4.7"),
                "rating_count": 178,
            },
            {
                "name": "Tinh Chất Dưỡng Ẩm Chiết Xuất Nha Đam",
                "slug": "cocoon-aloe-vera-serum",
                "description": "Dưỡng ẩm sâu, làm dịu da, phù hợp mọi loại da",
                "price": Decimal("195000"),
                "stock": 60,
                "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
                "category_id": categories[4].id,  # Serum
                "brand_id": brands[2].id,  # Cocoon
                "skin_types": ["normal", "dry", "sensitive", "combination"],
                "concerns": ["dehydration", "redness"],
                "key_ingredients": ["aloe_vera", "hyaluronic_acid"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 180,
                "rating_avg": Decimal("4.4"),
                "rating_count": 145,
            },
            {
                "name": "Green Tea Seed Toner",
                "slug": "innisfree-green-tea-seed-toner",
                "description": "Nước cân bằng dưỡng ẩm từ trà xanh",
                "price": Decimal("285000"),
                "stock": 45,
                "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
                "category_id": categories[5].id,  # Toner
                "brand_id": brands[3].id,  # Innisfree
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dehydration", "dullness"],
                "key_ingredients": ["green_tea", "hyaluronic_acid"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 220,
                "rating_avg": Decimal("4.5"),
                "rating_count": 189,
            },
            {
                "name": "Vitamin C Suspension 23% + HA Spheres 2%",
                "slug": "the-ordinary-vitamin-c-suspension",
                "description": "Serum Vitamin C dạng suspension, làm sáng da, giảm thâm nám",
                "price": Decimal("210000"),
                "stock": 30,
                "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
                "category_id": categories[4].id,  # Serum
                "brand_id": brands[0].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dark_spots", "dullness", "aging"],
                "key_ingredients": ["vitamin_c", "hyaluronic_acid"],
                "free_from": ["alcohol", "fragrance"],
                "variants": None,
                "sold_count": 130,
                "rating_avg": Decimal("4.2"),
                "rating_count": 98,
            },
            {
                "name": "Blue Leaf Toner",
                "slug": "innisfree-blue-leaf-toner",
                "description": "Nước cân bằng da từ lá bạc hà, kiểm soát bã nhờn",
                "price": Decimal("265000"),
                "stock": 38,
                "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
                "category_id": categories[5].id,  # Toner
                "brand_id": brands[3].id,
                "skin_types": ["oily", "combination"],
                "concerns": ["pores", "acne"],
                "key_ingredients": ["mint", "green_tea"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 95,
                "rating_avg": Decimal("4.3"),
                "rating_count": 72,
            },
            {
                "name": "Supple Preparation Toner",
                "slug": "klairs-supple-preparation-toner",
                "description": "Nước cân bằng dịu nhẹ, phù hợp da nhạy cảm",
                "price": Decimal("345000"),
                "stock": 42,
                "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
                "category_id": categories[5].id,  # Toner
                "brand_id": brands[4].id,  # Klairs
                "skin_types": ["sensitive", "dry", "normal", "combination"],
                "concerns": ["redness", "dehydration"],
                "key_ingredients": ["centella", "hyaluronic_acid", "beta_glucan"],
                "free_from": ["alcohol", "fragrance", "parabens", "colorant"],
                "variants": None,
                "sold_count": 165,
                "rating_avg": Decimal("4.6"),
                "rating_count": 134,
            },
            {
                "name": "Daily Moisturizing Lotion",
                "slug": "innisfree-daily-moisturizing-lotion",
                "description": "Kem dưỡng ẩm hàng ngày, nhẹ nhàng không nhờn",
                "price": Decimal("295000"),
                "stock": 55,
                "image_url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400",
                "category_id": categories[6].id,  # Moisturizer
                "brand_id": brands[3].id,
                "skin_types": ["normal", "combination", "dry"],
                "concerns": ["dehydration"],
                "key_ingredients": ["green_tea", "olive_oil"],
                "free_from": ["fragrance", "parabens"],
                "variants": None,
                "sold_count": 140,
                "rating_avg": Decimal("4.4"),
                "rating_count": 108,
            },
            {
                "name": "Moisturizing Factors + PM",
                "slug": "the-ordinary-moisturizing-factors-pm",
                "description": "Kem dưỡng ẩm ban đêm, không gây bít tắc lỗ chân lông",
                "price": Decimal("155000"),
                "stock": 48,
                "image_url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400",
                "category_id": categories[6].id,  # Moisturizer
                "brand_id": brands[0].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dehydration"],
                "key_ingredients": ["hyaluronic_acid", "ceramides", "natural_moisturizing_factors"],
                "free_from": ["alcohol", "fragrance", "oils", "silicons"],
                "variants": None,
                "sold_count": 110,
                "rating_avg": Decimal("4.3"),
                "rating_count": 85,
            },
            {
                "name": "Rich Moist Soothing Cream",
                "slug": "klairs-rich-moist-soothing-cream",
                "description": "Kem dưỡng ẩm sâu, làm dịu da nhạy cảm",
                "price": Decimal("385000"),
                "stock":35,
                "image_url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400",
                "category_id": categories[6].id,  # Moisturizer
                "brand_id": brands[4].id,
                "skin_types": ["dry", "sensitive", "normal"],
                "concerns": ["redness", "dehydration"],
                "key_ingredients": ["centella", "beta_glucan", "ceramides"],
                "free_from": ["alcohol", "fragrance", "parabens", "colorant"],
                "variants": None,
                "sold_count": 125,
                "rating_avg": Decimal("4.7"),
                "rating_count": 98,
            },
            {
                "name": "Mặt Nạ Ngủ Chiết Xuất Nha Đam",
                "slug": "cocoon-aloe-vera-sleeping-mask",
                "description": "Mặt nạ ngủ dưỡng ẩm qua đêm, phục hồi da",
                "price": Decimal("225000"),
                "stock":50,
                "image_url": "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=400",
                "category_id": categories[7].id,  # Mask
                "brand_id": brands[2].id,
                "skin_types": ["normal", "dry", "combination"],
                "concerns": ["dehydration", "dullness"],
                "key_ingredients": ["aloe_vera", "hyaluronic_acid"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 88,
                "rating_avg": Decimal("4.5"),
                "rating_count": 67,
            },
            {
                "name": "Gentle Black Sugar Scrub",
                "slug": "innisfree-gentle-black-sugar-scrub",
                "description": "Tẩy tế bào chết vật lý từ đường đen, mịn da",
                "price": Decimal("195000"),
                "stock":40,
                "image_url": "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?w=400",
                "category_id": categories[7].id,  # Mask
                "brand_id": brands[3].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dullness", "pores"],
                "key_ingredients": ["sugar", "black_tea"],
                "free_from": ["fragrance", "parabens"],
                "variants": None,
                "sold_count": 72,
                "rating_avg": Decimal("4.2"),
                "rating_count": 54,
            },
            {
                "name": "AHA 30% + BHA 2% Peeling Solution",
                "slug": "the-ordinary-aha-30-bha-2-peeling",
                "description": "Tẩy tế bào chết hóa học mạnh, cải thiện kết cấu da",
                "price": Decimal("275000"),
                "stock": 28,
                "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
                "category_id": categories[7].id,  # Mask
                "brand_id": brands[0].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["dullness", "dark_spots", "acne", "pores"],
                "key_ingredients": ["aha", "bha", "glycolic_acid", "lactic_acid", "salicylic_acid"],
                "free_from": ["alcohol", "fragrance"],
                "variants": None,
                "sold_count": 155,
                "rating_avg": Decimal("4.4"),
                "rating_count": 121,
            },
            {
                "name": "Hyalu B5 Serum",
                "slug": "la-roche-posay-hyalu-b5-serum",
                "description": "Serum cấp ẩm sâu với Hyaluronic Acid và Vitamin B5, phục hồi da",
                "price": Decimal("650000"),
                "stock": 32,
                "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400",
                "category_id": categories[4].id,  # Serum
                "brand_id": brands[1].id,  # La Roche-Posay
                "skin_types": ["dry", "sensitive", "normal", "combination"],
                "concerns": ["dehydration", "aging", "redness"],
                "key_ingredients": ["hyaluronic_acid", "vitamin_b5", "madecassoside"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 98,
                "rating_avg": Decimal("4.6"),
                "rating_count": 76,
            },
            {
                "name": "Retinol 0.5% in Squalane",
                "slug": "the-ordinary-retinol-0-5-squalane",
                "description": "Retinol chống lão hóa, giảm nếp nhăn, cải thiện kết cấu da",
                "price": Decimal("320000"),
                "stock": 25,
                "image_url": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400",
                "category_id": categories[4].id,  # Serum
                "brand_id": brands[0].id,
                "skin_types": ["normal", "oily", "combination"],
                "concerns": ["aging", "wrinkles", "dark_spots", "pores"],
                "key_ingredients": ["retinol", "squalane"],
                "free_from": ["alcohol", "fragrance", "nuts"],
                "variants": None,
                "sold_count": 145,
                "rating_avg": Decimal("4.5"),
                "rating_count": 112,
            },
            {
                "name": "Cicaplast Baume B5",
                "slug": "la-roche-posay-cicaplast-baume-b5",
                "description": "Kem phục hồi da đa năng, làm dịu và bảo vệ da tổn thương",
                "price": Decimal("380000"),
                "stock": 40,
                "image_url": "https://images.unsplash.com/photo-1557750255-c76072a7aad1?w=400",
                "category_id": categories[6].id,  # Moisturizer
                "brand_id": brands[1].id,
                "skin_types": ["sensitive", "dry", "normal"],
                "concerns": ["redness", "aging", "dehydration"],
                "key_ingredients": ["thermal_water", "vitamin_b5", "madecassoside"],
                "free_from": ["alcohol", "fragrance", "parabens", "lanolin"],
                "variants": None,
                "sold_count": 210,
                "rating_avg": Decimal("4.7"),
                "rating_count": 165,
            },
            {
                "name": "Centella Unscented Serum",
                "slug": "klairs-centella-unscented-serum",
                "description": "Serum rau má dịu nhẹ, không mùi, phục hồi da nhạy cảm",
                "price": Decimal("395000"),
                "stock": 28,
                "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400",
                "category_id": categories[4].id,  # Serum
                "brand_id": brands[4].id,
                "skin_types": ["sensitive", "dry", "normal", "combination"],
                "concerns": ["redness", "aging", "dehydration"],
                "key_ingredients": ["centella", "hyaluronic_acid"],
                "free_from": ["alcohol", "fragrance", "parabens", "colorant", "essential_oils"],
                "variants": None,
                "sold_count": 132,
                "rating_avg": Decimal("4.6"),
                "rating_count": 98,
            },
            {
                "name": "BHA Blackhead Power Liquid",
                "slug": "cosrx-bha-blackhead-power-liquid",
                "description": "Tẩy tế bào chết BHA, làm sạch mụn đầu đen, thu nhỏ lỗ chân lông",
                "price": Decimal("290000"),
                "stock": 50,
                "image_url": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400",
                "category_id": categories[5].id,  # Toner
                "brand_id": brands[4].id,  # Dùng chung brand Klairs cho mỹ phẩm Hàn
                "skin_types": ["oily", "combination", "normal"],
                "concerns": ["acne", "pores", "blackheads"],
                "key_ingredients": ["bha", "salicylic_acid", "betaine"],
                "free_from": ["alcohol", "fragrance", "parabens"],
                "variants": None,
                "sold_count": 187,
                "rating_avg": Decimal("4.5"),
                "rating_count": 143,
            },
        ]
        
        for prod_data in products_data:
            # Tach image_url ra de tao ProductImage rieng
            image_url = prod_data.pop("image_url", None)
            prod = Product(
                **prod_data,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(prod)
            await db.flush()  # Lay product.id

            if image_url:
                img = ProductImage(
                    product_id=prod.id,
                    public_id=_make_public_id(image_url, prod_data.get("slug", str(prod.id))),
                    url=image_url,
                    secure_url=image_url,
                    position=0,
                    is_main=True,
                )
                db.add(img)

        print(f"Created {len(products_data)} products with images")

        await db.commit()
        print("Seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())