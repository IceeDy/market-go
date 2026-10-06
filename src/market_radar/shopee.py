import hashlib
import hmac
import os
import time

import httpx


class ShopeeAPI:
    """Minimal Shopee Open Platform v2 client.

    Shop-level GET requests are signed with:
    partner_id + api_path + timestamp + access_token + shop_id
    using HMAC-SHA256 and the partner_key.
    """

    def __init__(
        self,
        partner_id=None,
        partner_key=None,
        access_token=None,
        shop_id=None,
        base=None,
        client=None,
    ):
        self.partner_id = int(partner_id or os.getenv("SHOPEE_PARTNER_ID", "0"))
        self.partner_key = partner_key or os.getenv("SHOPEE_PARTNER_KEY", "")
        self.access_token = access_token or os.getenv("SHOPEE_ACCESS_TOKEN", "")
        self.shop_id = int(shop_id or os.getenv("SHOPEE_SHOP_ID", "0"))
        self.base = (base or os.getenv(
            "SHOPEE_API_BASE_URL",
            "https://partner.shopeemobile.com",
        )).rstrip("/")
        self.client = client or httpx.Client(timeout=20)

    def _signature(self, path: str, timestamp: int) -> str:
        raw = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        return hmac.new(
            self.partner_key.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def get(self, path: str, **kwargs):
        if not self.partner_id or not self.partner_key:
            raise RuntimeError("SHOPEE_PARTNER_ID and SHOPEE_PARTNER_KEY are required")
        if not self.access_token or not self.shop_id:
            raise RuntimeError("SHOPEE_ACCESS_TOKEN and SHOPEE_SHOP_ID are required")

        timestamp = int(time.time())
        params = dict(kwargs.pop("params", {}) or {})
        params.update({
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self.access_token,
            "shop_id": self.shop_id,
            "sign": self._signature(path, timestamp),
        })
        response = self.client.get(self.base + path, params=params, **kwargs)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(
                f"Shopee API error: {data.get('error')}: {data.get('message', '')}".strip()
            )
        return data

    def product_list(self, offset=0, page_size=20, item_status="NORMAL"):
        return self.get(
            "/api/v2/product/get_item_list",
            params={
                "offset": max(0, offset),
                "page_size": min(max(1, page_size), 100),
                "item_status": item_status,
            },
        )

    def product_base_info(self, item_ids):
        ids = list(item_ids)
        if not ids:
            return {"item_list": []}
        return self.get(
            "/api/v2/product/get_item_base_info",
            params={"item_id_list": ",".join(str(x) for x in ids[:50])},
        )

    def categories(self, language="pt-BR"):
        return self.get(
            "/api/v2/product/get_category",
            params={"language": language},
        )
