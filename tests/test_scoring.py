from market_radar.scoring import commercial_score, opportunity_score

def test_opportunity_score_range():
    assert opportunity_score(100, 100, 100, 100, 100, 100, 100) == 100

def test_commercial_score_prefers_margin():
    assert commercial_score(100, 30, 1, 4, 3) > commercial_score(100, 80, 1, 4, 3)
