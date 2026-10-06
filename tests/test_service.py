from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from market_radar.db import Base
from market_radar import service

def test_persistence_and_trending(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(service, "SessionLocal", Session)
    from market_radar.core import MLProduct
    service.persist_search([MLProduct("MLB1","Produto",price=100,position=5)])
    service.persist_search([MLProduct("MLB1","Produto",price=110,position=2)])
    rows = service.trending_opportunities()
    assert rows[0]["external_id"] == "MLB1"
    assert rows[0]["rank_delta"] == 3
    assert rows[0]["score"] > 50
