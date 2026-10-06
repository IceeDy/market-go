from market_radar.economics import SourcingScenario, economics

def test_landed_cost():
    scenario = SourcingScenario(unit_cost=20, international_freight_per_unit=5, import_tax_pct=20, domestic_cost_per_unit=2)
    assert scenario.landed_cost == 32

def test_profit_margin_and_roi():
    scenario = SourcingScenario(unit_cost=20, marketplace_fee_pct=15, shipping_cost_per_unit=5)
    result = economics(100, scenario)
    assert result["landed_cost"] == 20
    assert result["marketplace_fee"] == 15
    assert result["profit"] == 60
    assert result["margin_pct"] == 60
    assert result["roi_pct"] == 300
