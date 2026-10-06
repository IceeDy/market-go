import httpx
from market_radar.core import MercadoLivre,trend_score

def test_bulk():
    def h(r): return httpx.Response(200,json=[{"id":"MLB1","status_code":200,"body":{"id":"MLB1","title":"Teste"}}])
    c=MercadoLivre(client=httpx.Client(transport=httpx.MockTransport(h)))
    assert c.bulk_items(["MLB1"])["MLB1"]["title"]=="Teste"

def test_trend_score():
    assert trend_score(2,5,0,3)>50
