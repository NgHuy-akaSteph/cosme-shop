"""Registry cac cong thanh toan"""

from app.payment.base import PaymentProvider
from app.payment.sepay_provider import SePayProvider

_PROVIDERS: dict[str, PaymentProvider] = {
    "sepay": SePayProvider(),
}


def get_provider(name: str | None = None) -> PaymentProvider:
    """
    Tra ve provider theo ten (mac dinh theo payment_method cua don).

    Sau nay them payOS: chi can dang ky vao _PROVIDERS.
    """
    key = name or "sepay"
    provider = _PROVIDERS.get(key)
    if provider is None:
        raise KeyError(f"Payment provider chua duoc ho tro: {key}")
    return provider
