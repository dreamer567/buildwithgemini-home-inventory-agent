"""Unit tests for home inventory tools."""

from app.tools import (
    add_item,
    check_inventory_alerts,
    compare_in_use_vs_backup_stock,
    generate_shopping_plan,
    get_room_furniture_layout,
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
    # 抽纸 is low stock (quantity 1, min_threshold 2)
    assert any("抽纸" in item["name"] for item in res["low_stock_items"])


def test_generate_shopping_plan():
    plan = generate_shopping_plan()
    assert plan["status"] == "success"
    assert "urgent_replenishment" in plan
    assert len(plan["urgent_replenishment"]) >= 1


def test_get_room_furniture_layout_all():
    res = get_room_furniture_layout()
    assert res["status"] == "success"
    assert res["matched_count"] >= 5
    assert "中卧主卧" in res["rooms"]
    master = res["rooms"]["中卧主卧"]
    assert any("押入壁橱" in f["piece"] for f in master["furniture_layout"])


def test_get_room_furniture_layout_specific():
    res = get_room_furniture_layout("书房")
    assert res["status"] == "success"
    assert "东卧书房" in res["rooms"]
    study = res["rooms"]["东卧书房"]
    assert any("书桌" in f["piece"] for f in study["furniture_layout"])


def test_compare_in_use_vs_backup_stock():
    res = compare_in_use_vs_backup_stock()
    assert res["status"] == "success"
    assert len(res["comparisons"]) >= 3
    # Check tissue comparison
    tissue_comp = next((c for c in res["comparisons"] if "抽纸" in c["item_category"]), None)
    assert tissue_comp is not None
    assert "LDK" in tissue_comp["in_use_status"]
    assert "西卧" in tissue_comp["backup_storage_status"]
