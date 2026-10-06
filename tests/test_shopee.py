from market_radar.shopee import ShopeeAPI


def test_shopee_signature():
    api = ShopeeAPI(
        partner_id=123,
        partner_key="secret",
        access_token="token",
        shop_id=456,
    )
    assert len(api._signature("/api/v2/product/get_item_list", 1700000000)) == 64


def test_shopee_product_list_uses_signed_get():
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": {"item": []}}

    class FakeClient:
        def __init__(self):
            self.url = None
            self.params = None

        def get(self, url, **kwargs):
            self.url = url
            self.params = kwargs["params"]
            return FakeResponse()

    fake = FakeClient()
    api = ShopeeAPI(
        partner_id=123,
        partner_key="secret",
        access_token="token",
        shop_id=456,
        client=fake,
    )
    result = api.product_list(page_size=10)

    assert result["response"]["item"] == []
    assert fake.url.endswith("/api/v2/product/get_item_list")
    assert fake.params["partner_id"] == 123
    assert fake.params["shop_id"] == 456
    assert fake.params["page_size"] == 10
    assert len(fake.params["sign"]) == 64
