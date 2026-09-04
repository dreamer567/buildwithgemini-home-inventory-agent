"""Household inventory, storage advice, and shopping plan tools."""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_FILE = Path(__file__).parent / "inventory_data.json"


def _load_data() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_data(items: List[Dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def search_item(query: str) -> Dict[str, Any]:
    """搜索物品的存放位置、数量和状态。例如查找'指甲刀'、'钥匙'、'感冒药'放在哪里。

    Args:
        query: 要搜索的物品名称、类别、或存放位置关键词。

    Returns:
        匹配到的物品列表及其存放位置、剩余数量、保质期和备注信息。
    """
    items = _load_data()
    q = query.strip().lower()
    matches = []

    for item in items:
        name = item.get("name", "").lower()
        cat = item.get("category", "").lower()
        loc = item.get("location", "").lower()
        notes = item.get("notes", "").lower()

        if q in name or q in cat or q in loc or q in notes:
            matches.append(item)

    if not matches:
        return {
            "status": "not_found",
            "message": f"未在当前物品清单中找到与 '{query}' 相关的物品。你可以告诉我将其添加到哪个位置。",
            "results": [],
        }

    return {
        "status": "success",
        "count": len(matches),
        "results": matches,
    }


def list_inventory(category: str = "", location: str = "") -> Dict[str, Any]:
    """查看当前所有资产与物品清单，支持按分类或位置筛选。

    Args:
        category: 可选筛选类别，如'食品蔬菜水果'、'日用品'、'资产与常备品'、'常备药品'。
        location: 可选筛选位置，如'冰箱'、'厨房'、'客厅'、'卧室'。

    Returns:
        符合条件的物品总览及详细列表。
    """
    items = _load_data()
    results = []
    cat_filter = category.strip().lower()
    loc_filter = location.strip().lower()

    for item in items:
        match_cat = not cat_filter or cat_filter in item.get("category", "").lower()
        match_loc = not loc_filter or loc_filter in item.get("location", "").lower()
        if match_cat and match_loc:
            results.append(item)

    return {
        "status": "success",
        "total_items": len(results),
        "items": results,
    }


def add_item(
    name: str,
    category: str,
    location: str,
    quantity: float,
    unit: str = "个",
    expiry_date: str = "",
    min_threshold: float = 1.0,
    notes: str = "",
) -> Dict[str, Any]:
    """录入新增物品或资产。

    Args:
        name: 物品名称（如'洗洁精'、'红富士苹果'、'指甲刀'）。
        category: 类别（如'食品蔬菜水果'、'日用品'、'资产与常备品'、'常备药品'）。
        location: 具体收纳位置（如'厨房水槽下左侧收纳盒'、'客厅茶几第二层抽屉'）。
        quantity: 数量或余量。
        unit: 单位，如'个'、'包'、'瓶'、'枚'、'盒'。
        expiry_date: 过期日期，格式YYYY-MM-DD（若是保质期生鲜或药品，请提供）。
        min_threshold: 最低安全库存警戒线，默认1.0。
        notes: 补充备注，如品牌、规格或储存要求。

    Returns:
        录入结果确认。
    """
    items = _load_data()
    new_id = f"item_{len(items) + 1:03d}"
    new_item = {
        "id": new_id,
        "name": name,
        "category": category,
        "location": location,
        "quantity": quantity,
        "unit": unit,
        "expiry_date": expiry_date,
        "min_threshold": min_threshold,
        "notes": notes,
    }
    items.append(new_item)
    _save_data(items)
    return {"status": "success", "message": f"成功录入物品: {name}", "item": new_item}


def update_item(
    name: str,
    quantity: Optional[float] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """更新物品的数量/余量、存放位置或备注信息。

    Args:
        name: 物品名称（支持模糊匹配）。
        quantity: 新的数量/余量（若用完可设为0）。
        location: 新的收纳位置。
        notes: 新的备注或注意事项。

    Returns:
        更新结果及最新物品信息。
    """
    items = _load_data()
    target = None
    target_idx = -1

    for idx, item in enumerate(items):
        if name.lower() in item.get("name", "").lower():
            target = item
            target_idx = idx
            break

    if not target:
        return {"status": "error", "message": f"未找到名为 '{name}' 的物品。"}

    if quantity is not None:
        target["quantity"] = quantity
    if location:
        target["location"] = location
    if notes:
        target["notes"] = notes

    items[target_idx] = target
    _save_data(items)
    return {"status": "success", "message": f"物品 '{target['name']}' 已更新。", "item": target}


def get_storage_advice(item_name: str) -> Dict[str, Any]:
    """获取物品、食品或日用品的专业储藏与保鲜建议。

    Args:
        item_name: 物品或食材名称（如'西红柿'、'香蕉'、'土豆'、'鸡蛋'、'电池'、'药品'）。

    Returns:
        包含最佳存放位置、温度要求、保鲜秘诀与避免误区的详细指南。
    """
    item_lower = item_name.strip().lower()

    # 常见食材与日用品的科学存放知识库
    advice_db = {
        "西红柿": {
            "best_location": "常温通风避光处（果蒂朝下放置）",
            "temperature": "12°C ~ 18°C 室温",
            "avoid": "千万别放冷藏室！冷藏破坏细胞膜导致肉质发面、风味芳香物质完全流失。",
            "tips": "未完全熟透的西红柿常温催熟；完全熟透且来不及吃，可切块冷冻用于煮汤煮面。",
        },
        "香蕉": {
            "best_location": "阴凉通风处，悬挂或拱面朝上摆放",
            "temperature": "常温 15°C ~ 20°C",
            "avoid": "切忌直接放冰箱冷藏，低温会使香蕉皮迅速褐变黑化并冻伤果肉；不要与苹果等高乙烯水果紧挨着。",
            "tips": "用保鲜膜紧紧包裹香蕉根部根茎，可阻隔乙烯释放，延长3~5天保鲜期。",
        },
        "土豆": {
            "best_location": "阴凉、干燥、通风、避光的纸箱或布袋中",
            "temperature": "常温 7°C ~ 12°C 避光",
            "avoid": "绝对不能受光照（遇光产生龙葵碱剧毒发绿）；不要与红薯或洋葱混放。",
            "tips": "在土豆箱里放一个成熟的苹果，苹果释放的微量乙烯能有效抑制土豆发芽。",
        },
        "鸡蛋": {
            "best_location": "冰箱冷藏室内部专用蛋盒，大头朝上",
            "temperature": "2°C ~ 5°C 冷藏",
            "avoid": "不要放在冰箱门侧蛋架（门开合频繁温差大易变质）；存放前切忌水洗（会洗掉蛋壳保护膜导致细菌侵入）。",
            "tips": "大头是气室所在，大头朝上能使蛋黄处于中间，延缓蛋黄贴壳变质。",
        },
        "面包": {
            "best_location": "分装密封放冷冻室（-18°C），吃前复烤",
            "temperature": "室温（2天内）或冷冻（长期）",
            "avoid": "切勿放冷藏室！冷藏温度（2°C~6°C）是淀粉老化回生最快的温区，会让面包迅速变得干燥粗糙硬邦邦。",
            "tips": "买回大份面包先按每次食用量切片，密封袋冷冻，吃时无需解冻直接平底锅或烤箱加热即恢复松软。",
        },
        "布洛芬": {
            "best_location": "干燥阴凉避光的抽屉或专用药箱",
            "temperature": "常温密封（10°C ~ 25°C）",
            "avoid": "不要放在浴室或湿气重的地方，湿气易导致胶囊软化粘连变质。",
            "tips": "保留原包装与说明书，定期检查包装印制的有效期限。",
        },
        "药品": {
            "best_location": "专用家庭避光小药箱，置于儿童不易触及的高处或抽屉",
            "temperature": "常温避光干燥（除非明确标注需2-8°C冷藏如未开封胰岛素或某些活菌）",
            "avoid": "不要放在阳光直射阳台、湿润的卫生间或厨房灶台旁。",
            "tips": "开封后的药瓶内的棉花和干燥剂应立即丢弃，避免反复吸收外界潮气。",
        },
        "电池": {
            "best_location": "干燥阴凉的密封收纳盒中",
            "temperature": "室温干燥 10°C ~ 20°C",
            "avoid": "避免高温高湿；避免正负极混杂裸露接触金属物品引起短路。",
            "tips": "长期不用的电器（遥控器、游戏手柄）务必取出电池，防止漏液腐蚀电路板。",
        },
    }

    matched_key = None
    for k in advice_db:
        if k in item_lower:
            matched_key = k
            break

    if matched_key:
        advice = advice_db[matched_key]
        return {
            "item": item_name,
            "status": "matched",
            "advice": advice,
        }

    # 通用常识原则
    return {
        "item": item_name,
        "status": "general_guideline",
        "general_advice": (
            "1. 生鲜肉类/开封牛奶/绿叶蔬菜：及时冷藏（0~4°C）或分装冷冻；\n"
            "2. 热带水果与根茎类（香蕉、芒果、洋葱、土豆）：适合阴凉避光通风常温保存；\n"
            "3. 调味品：含水含糖高（如蚝油、沙拉酱、番茄酱）开封后必须冷藏；高盐酱油、醋常温密封即可；\n"
            "4. 日用耗材与数码药品：遵循'避光、干燥、分类隔层收纳'原则。"
        ),
    }


def check_inventory_alerts(expiring_within_days: int = 5) -> Dict[str, Any]:
    """一键盘点临期食品、药品以及库存见底的日用品。

    Args:
        expiring_within_days: 预警天数阈值，默认为未来5天内过期的物品。

    Returns:
        包含已过期物品、即将过期物品、库存告急物品的分类清单与统计。
    """
    items = _load_data()
    today = datetime.date.today()
    threshold_date = today + datetime.timedelta(days=expiring_within_days)

    expired_items = []
    expiring_soon_items = []
    low_stock_items = []

    for item in items:
        # 1. 检查库存量告急
        qty = item.get("quantity", 0)
        min_th = item.get("min_threshold", 1)
        if qty <= min_th:
            low_stock_items.append({
                "name": item.get("name"),
                "category": item.get("category"),
                "quantity": f"{qty} {item.get('unit', '')}",
                "min_threshold": f"{min_th} {item.get('unit', '')}",
                "location": item.get("location"),
                "notes": item.get("notes", ""),
            })

        # 2. 检查保质期
        exp_str = item.get("expiry_date", "").strip()
        if exp_str:
            try:
                exp_date = datetime.datetime.strptime(exp_str, "%Y-%m-%d").date()
                days_left = (exp_date - today).days

                if days_left < 0:
                    expired_items.append({
                        "name": item.get("name"),
                        "category": item.get("category"),
                        "location": item.get("location"),
                        "expiry_date": exp_str,
                        "days_overdue": abs(days_left),
                    })
                elif days_left <= expiring_within_days:
                    expiring_soon_items.append({
                        "name": item.get("name"),
                        "category": item.get("category"),
                        "location": item.get("location"),
                        "expiry_date": exp_str,
                        "days_left": days_left,
                        "quantity": f"{qty} {item.get('unit', '')}",
                    })
            except ValueError:
                pass

    return {
        "status": "success",
        "current_date": str(today),
        "summary": {
            "expired_count": len(expired_items),
            "expiring_soon_count": len(expiring_soon_items),
            "low_stock_count": len(low_stock_items),
        },
        "expired_items": expired_items,
        "expiring_soon_items": expiring_soon_items,
        "low_stock_items": low_stock_items,
    }


def generate_shopping_plan() -> Dict[str, Any]:
    """基于当前余量告急日用品和即将耗尽/过期的生鲜食材，自动生成分类采购补货计划。

    Returns:
        按优先级分类的采购清单（紧急补货、日常采购、备选更新）。
    """
    alerts = check_inventory_alerts(expiring_within_days=4)
    low_stock = alerts.get("low_stock_items", [])
    expiring = alerts.get("expiring_soon_items", [])

    urgent_list = []
    normal_list = []
    replace_list = []

    # 处理库存告急物品
    for item in low_stock:
        cat = item.get("category", "")
        plan_entry = {
            "name": item.get("name"),
            "category": cat,
            "current_status": f"当前仅剩: {item.get('quantity')}",
            "recommended_buy": "建议采购 1~2 份补足日常用量",
            "reason": "余量触底",
        }
        if "日用" in cat or "洁" in item.get("name") or "纸" in item.get("name"):
            plan_entry["priority"] = "🔴 紧急补货"
            urgent_list.append(plan_entry)
        else:
            plan_entry["priority"] = "🟡 常规补货"
            normal_list.append(plan_entry)

    # 处理即将过期的生鲜
    for item in expiring:
        replace_list.append({
            "name": item.get("name"),
            "category": item.get("category"),
            "current_status": f"剩余保质期 {item.get('days_left')} 天 ({item.get('quantity')})",
            "recommended_action": "近期需尽快吃完，吃完后视食欲采购新鲜份量",
            "priority": "🟢 饮食消耗与交替",
        })

    return {
        "status": "success",
        "generated_at": str(datetime.date.today()),
        "urgent_replenishment": urgent_list,
        "routine_restock": normal_list,
        "perishable_consumption_or_replace": replace_list,
        "tips_for_family_living": "三口之家采购小贴士：绿叶蔬菜与生鲜水果按全家2-3天消耗量适量采购，保证营养与新鲜；抽纸、洗洁精、洗衣液等高频消耗品可按家庭装备货囤入西卧储物间。",
    }
