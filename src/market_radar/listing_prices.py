from .core import MercadoLivre


def listing_prices(
    client: MercadoLivre,
    category_id: str,
    price: float,
    currency_id: str = "BRL",
    listing_type_id: str = "gold_special",
    logistic_type: str | None = None,
    shipping_mode: str | None = None,
) -> list[dict]:
    params = {
        "category_id": category_id,
        "price": price,
        "currency_id": currency_id,
        "listing_type_id": listing_type_id,
    }
    if logistic_type:
        params["logistic_type"] = logistic_type
    if shipping_mode:
        params["shipping_mode"] = shipping_mode
    data = client.get(f"/sites/{client.site}/listing_prices", params=params)
    return data if isinstance(data, list) else [data]
