from outlier.finance.calc import (
    AcquisitionInputs,
    PlatformFees,
    ResaleInputs,
    Thresholds,
    compute,
    risk_adjusted_value,
    sensitivity,
)

EBAY = PlatformFees(name="ebay", final_value_fee_pct=13.25, per_order_fee=0.40, seller_pays_shipping=True)
LOCAL = PlatformFees(name="local", final_value_fee_pct=0, per_order_fee=0, seller_pays_shipping=False)
THR = Thresholds(min_profit_usd=25, min_roi_pct=50, max_capital_at_risk_usd=250, bid_increment=1.0)


def test_basic_profit_and_max_bid():
    a = AcquisitionInputs(bid=20, sales_tax_pct=0, incoming_shipping=12.0, handling_fee=1.0)
    r = ResaleInputs(resale_price=150, outgoing_shipping=10, packaging_cost=1)
    res = compute(a, r, EBAY, THR)
    assert res.acquisition_total == 33.0
    # fees: 150*0.1325 + 0.40 = 20.275 ; costs 11 ; net = 118.725
    assert abs(res.net_proceeds - 118.73) < 0.02
    assert abs(res.profit - 85.73) < 0.02
    assert res.roi_pct > 250
    assert res.complete is True
    assert res.unknown_costs == []
    # break-even bid: net - fixed(13) = 105.725
    assert abs(res.break_even_bid - 105.73) < 0.02
    # max bid: min_profit -> 105.725-25 = 80.7 ; min_roi -> 118.725/1.5 - 13 = 66.15 ; cap -> 250-13=237
    assert res.max_bid == 66.0
    assert res.max_bid_binding_constraint == "min_roi"


def test_tax_and_premium_scale_bid():
    a = AcquisitionInputs(bid=100, buyer_premium_pct=10, sales_tax_pct=8, incoming_shipping=0, handling_fee=0)
    r = ResaleInputs(resale_price=300, outgoing_shipping=0, packaging_cost=0)
    res = compute(a, r, LOCAL, THR)
    assert abs(res.acquisition_total - 118.8) < 0.01  # 100*1.1*1.08
    assert res.net_proceeds == 300
    # min_roi: 300/1.5 /1.188 = 168.35 ; min_profit: (300-25)/1.188 = 231.4 ; cap: 250/1.188=210.4
    assert res.max_bid == 168.0


def test_unknown_shipping_is_flagged_not_silently_zeroed():
    a = AcquisitionInputs(bid=10)
    r = ResaleInputs(resale_price=80)
    res = compute(a, r, EBAY, THR)
    assert "incoming_shipping" in res.unknown_costs
    assert "outgoing_shipping" in res.unknown_costs
    assert res.complete is False
    assert any("Unknown costs" in n for n in res.notes)


def test_assumed_defaults_are_reported():
    a = AcquisitionInputs(bid=10)
    r = ResaleInputs(resale_price=80)
    res = compute(a, r, EBAY, THR, assumed={"incoming_shipping": 14.0, "outgoing_shipping": 9.5})
    assert res.assumed_costs == {"incoming_shipping": 14.0, "outgoing_shipping": 9.5}
    assert res.complete is True
    assert res.acquisition_breakdown["incoming_shipping"] == 14.0


def test_no_resale_value_gives_incomplete():
    res = compute(AcquisitionInputs(bid=10, incoming_shipping=5), ResaleInputs(resale_price=None), EBAY, THR)
    assert res.profit is None and res.max_bid is None and res.complete is False


def test_expensive_shipping_kills_margin():
    # jacket with strong comps but $60 shipping
    a = AcquisitionInputs(bid=30, incoming_shipping=60, handling_fee=2)
    r = ResaleInputs(resale_price=120, outgoing_shipping=18, packaging_cost=2)
    res = compute(a, r, EBAY, THR)
    assert res.profit < 25
    assert res.max_bid < 30  # current bid already above recommended max


def test_max_bid_zero_when_thresholds_impossible():
    a = AcquisitionInputs(bid=5, incoming_shipping=30, handling_fee=0)
    r = ResaleInputs(resale_price=40, outgoing_shipping=10, packaging_cost=1)
    res = compute(a, r, EBAY, THR)
    assert res.max_bid == 0.0
    assert any("No bid satisfies" in n for n in res.notes)


def test_depop_style_buyer_pays_shipping():
    depop = PlatformFees(name="depop", final_value_fee_pct=0, per_order_fee=0, payment_processing_pct=3.3, payment_processing_fixed=0.45, seller_pays_shipping=False)
    res = compute(AcquisitionInputs(bid=10, incoming_shipping=8, handling_fee=0), ResaleInputs(resale_price=100), depop, THR)
    assert "outgoing_shipping" not in res.unknown_costs
    assert abs(res.selling_fees - 3.75) < 0.01


def test_risk_adjusted_value_heuristic():
    v, meta = risk_adjusted_value(80, 120, 180, "high", 0.9, {"high": [0.25, 0.6, 0.15]}, 0.5)
    # blended = 20+72+27 = 119 ; haircut = 0.1*0.5 = 5% -> 113.05
    assert abs(v - 113.05) < 0.01
    assert meta["label"].startswith("heuristic")
    assert risk_adjusted_value(None, None, None, "none", None, {"none": [1, 0, 0]})[0] is None


def test_sensitivity_grid():
    rows = sensitivity(AcquisitionInputs(bid=10, handling_fee=1), ResaleInputs(resale_price=100, outgoing_shipping=10), EBAY, THR, None, [80, 120], [5, 15])
    assert len(rows) == 4
    assert rows[0]["max_bid"] < rows[2]["max_bid"]  # higher resale => higher max bid
    assert rows[0]["max_bid"] > rows[1]["max_bid"]  # higher shipping => lower max bid
