"""Unit tests for home inventory tools."""

from app.tools import (
    add_item,
    check_inventory_alerts,
    generate_shopping_plan,
    get_storage_advice,
    list_inventory,
    search_item,
    update_item,
)


def test_search_item_found():
    res = search_item("指甲刀")
    assert res["status"] == "success"
    assert res["count"] >= 1
    assert any("书桌" in item["location"] for item in res["results"])


def test_search_item_not_found():
    res = search_item("不存在的火星飞船")
    assert res["status"] == "not_found"
    assert res["results"] == []


def test_list_inventory():
    res = list_inventory(category="食品蔬菜水果")
    assert res["status"] == "success"
    assert res["total_items"] >= 1


def test_get_storage_advice():
    res_tomato = get_storage_advice("西红柿")
    assert res_tomato["status"] == "matched"
    assert "常温" in res_tomato["advice"]["best_location"]

    res_banana = get_storage_advice("香蕉")
    assert res_banana["status"] == "matched"
    assert "常温" in res_banana["advice"]["temperature"]


def test_check_inventory_alerts():
    res = check_inventory_alerts(expiring_within_days=7)
    assert res["status"] == "success"
    assert "low_stock_items" in res
    assert "expiring_soon_items" in res
    # 抽纸 is low stock (quantity 1, min_threshold 3)
    assert any("抽纸" in item["name"] for item in res["low_stock_items"])


def test_generate_shopping_plan():
    plan = generate_shopping_plan()
    assert plan["status"] == "success"
    assert "urgent_replenishment" in plan
    assert len(plan["urgent_replenishment"]) >= 1
