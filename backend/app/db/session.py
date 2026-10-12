from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# Tạo async engine với connection pooling
# Tối ưu cho Neon Free Tier: ít connection + auto-recycle + pre-ping
# để tránh lỗi "SSL connection has been closed" khi Neon kill idle connections
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,           # Giữ 5 connection thường trực
    max_overflow=5,        # Burst tối đa 5 connection thêm
    pool_pre_ping=True,    # Kiểm tra connection còn sống trước khi dùng
    pool_recycle=300,      # Recycle connection mỗi 5 phút (Neon đóng idle sau vài phút)
    echo=False,            # Tắt SQL log; bật True khi debug
    # Neon + PgBouncer yeu cau statement_cache_size=0 de tranh loi
    # "cached statement plan is invalid" khi schema thay doi.
    connect_args={"statement_cache_size": 0},
)

# Tạo async session maker
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Import all models để SQLAlchemy register đầy đủ mapper.
# Cần thiết để resolve forward string refs (vd: Product.images_rel -> ProductImage.position)
from app.model.user import User  # noqa: F401, E402
from app.model.category import Category  # noqa: F401, E402
from app.model.brand import Brand  # noqa: F401, E402
from app.model.product import Product  # noqa: F401, E402
from app.model.product_image import ProductImage  # noqa: F401, E402
from app.model.order import Order  # noqa: F401, E402
from app.model.order_item import OrderItem  # noqa: F401, E402
from app.model.order_status_history import OrderStatusHistory  # noqa: F401, E402
from app.model.wishlist import Wishlist  # noqa: F401, E402


# Dependency để lấy DB session trong các API route
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
