from market_radar.import_ranking import ImportBudget, rank_import_candidates


def test_budget_ranking_uses_reserve():
    candidates = [
        {"external_id": "A", "title": "A", "selling_price": 100, "unit_cost": 20},
        {"external_id": "B", "title": "B", "selling_price": 100, "unit_cost": 40},
    ]
    result = rank_import_candidates(candidates, ImportBudget(budget=1000, reserve_pct=10))

    assert result[0]["external_id"] == "A"
    assert result[0]["capital_invested"] == 900
    assert result[0]["units"] == 45
    assert result[0]["profit_potential"] == 3600


def test_mercado_livre_fee_overrides_manual_fee():
    candidate = {
        "external_id": "A",
        "selling_price": 100,
        "unit_cost": 20,
        "marketplace_fee_amount": 20,
        "marketplace_fee_pct": 5,
        "marketplace_fee_source": "mercado_livre",
    }
    result = rank_import_candidates(candidate and [candidate], ImportBudget(budget=1000, reserve_pct=0))

    assert result[0]["marketplace_fee"] == 20
    assert result[0]["marketplace_fee_source"] == "mercado_livre"
    assert result[0]["profit_per_unit"] == 60
