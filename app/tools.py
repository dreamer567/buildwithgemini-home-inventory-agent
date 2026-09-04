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


# ==============================================================================
# 🏠 3LDK 全屋家具布局、收纳层级与动线规则知识库 (Furniture & Storage Hierarchy)
# ==============================================================================
ROOM_FURNITURE_DIRECTORY: Dict[str, Dict[str, Any]] = {
    "玄关": {
        "name": "🚪 玄关与走廊 (Entrance & Foyer)",
        "english_name": "Entrance & Foyer",
        "japanese_name": "玄関・廊下",
        "zone_type": "入户缓冲与日常动线区",
        "family_function": "外出归家过渡、外穿衣帽鞋履更替、快递拆箱与重要凭证暂存",
        "furniture_layout": [
            {
                "piece": "悬空定制三段式鞋柜",
                "sub_zones": [
                    {"level": "顶层高柜", "usage": "换季鞋盒、备用鞋油鞋刷、室内访客备用拖鞋"},
                    {"level": "中段开放随手置物台", "usage": "钥匙收纳盘（家门备用钥匙）、认印印章盒、外出便携消毒喷雾、口罩盒"},
                    {"level": "底段悬空常穿位", "usage": "一家三口日常高频穿着鞋靴、居家拖鞋（便于一脚蹬换）"},
                ],
            },
            {
                "piece": "玄关独立落地挂衣架 / 外套专挂区",
                "sub_zones": [
                    {"level": "主挂衣杆/高位挂钩", "usage": "一家三口当季常穿外出大衣、羽绒服、防风夹克（归家即脱换，防尘洁净动线）"},
                    {"level": "中低位挂钩与置物层", "usage": "儿童常穿外套、遮阳帽、棒球帽、随身双肩小背包"},
                ],
            },
            {
                "piece": "入户胡桃木磁吸挂钩排",
                "sub_zones": [
                    {"level": "左侧挂钩", "usage": "长柄雨伞、折叠伞专用收纳袋"},
                    {"level": "右侧磁吸位", "usage": "拆快递专用防飞溅剪刀、环保购物帆布袋"},
                ],
            },
            {
                "piece": "弱电与配电箱暗盒",
                "sub_zones": [
                    {"level": "箱内收纳", "usage": "千兆光猫路由器、备用保险丝与门禁卡电池"},
                ],
            },
        ],
        "inventory_rules": "归家外套随手悬挂于玄关挂衣架，进门脱换阻断室外灰尘；钥匙与印章必须置于中段收纳盘；拆箱剪刀高位磁吸吸附，严防幼儿随意碰触。",
    },
    "LDK客餐厨": {
        "name": "🛋️ LDK 客餐厨 (Living, Dining & Kitchen)",
        "english_name": "Living, Dining & Kitchen",
        "japanese_name": "LDK・リビングダイニングキッチン",
        "zone_type": "核心家庭生活与餐饮区",
        "family_function": "一家三口用餐、互动娱乐、烹饪料理、零食点心享用与全家营养食材保鲜",
        "furniture_layout": [
            {
                "piece": "1.7米白橡木家庭大餐桌 + 4张餐椅 + 2张折叠备用凳",
                "sub_zones": [
                    {"level": "餐桌中央置物托盘", "usage": "水果盘（常温香蕉/苹果）、在用原木抽纸盒、隔热餐垫"},
                    {"level": "桌底收纳悬挂抽屉", "usage": "客厅空调遥控器、便携指甲锉、随手记事便签"},
                ],
            },
            {
                "piece": "三人位亲肤布艺沙发 + 可移动极简边几",
                "sub_zones": [
                    {"level": "沙发靠背储物袋", "usage": "投影仪遥控器、平板支架、亲子绘本与抱枕靠垫"},
                    {"level": "移动边几台面与底层", "usage": "家用高清投影仪（直投客厅正向主墙面）、多口快充无线充电板"},
                    {"level": "沙发与餐桌过道", "usage": "落地变频静音循环扇（在用）"},
                ],
            },
            {
                "piece": "450L 双门风冷无霜智能冰箱",
                "sub_zones": [
                    {"level": "冷藏室上层/中层 (2°C~5°C)", "usage": "鲜牛奶(1L)、即食酸奶、开封调味酱料、熟食密封保鲜盒"},
                    {"level": "保鲜果蔬抽屉 (6°C~8°C)", "usage": "高湿绿叶蔬菜、彩椒、胡萝卜、蓝莓水果"},
                    {"level": "冰箱门内侧蛋架与深层瓶架", "usage": "可生食鸡蛋8枚（大头朝上）、开封万能味醂、纯正生抽、番茄沙司"},
                    {"level": "超低温速冻抽屉 (-18°C)", "usage": "儿童辅食肉泥、原切牛排、分装肉糜、冷冻三文鱼片"},
                ],
            },
            {
                "piece": "厨房多层零食杂物抽屉柜 (家庭专属零食角)",
                "sub_zones": [
                    {"level": "第一层 (成人健康与提神零食)", "usage": "每日坚果便携包、挂耳黑咖啡、无糖薄荷糖、高纤苏打饼干"},
                    {"level": "第二层 (儿童营养与趣味加餐)", "usage": "原味高钙海苔、无添加山楂棒、小袋溶豆饼干（干燥避光，方便定量给予）"},
                    {"level": "第三层深抽屉 (耐储大包装与封口配件)", "usage": "大包坚果薯片备品、食品密封保鲜夹、便携自封袋"},
                ],
            },
            {
                "piece": "一体化橱柜烹饪系统 (阻尼拉篮 + 水槽柜 + 吊柜)",
                "sub_zones": [
                    {"level": "灶台下方双层阻尼拉篮", "usage": "万能味醂、特级初榨橄榄油、料理清酒、生抽老抽、平底不粘锅、深炖锅"},
                    {"level": "水槽下方防水不锈钢抽屉柜", "usage": "浓缩去油洗洁精(在用)、点断式加厚垃圾袋、百洁布洗碗海绵、厨余沥水网袋"},
                    {"level": "厨房通风台面/置物架", "usage": "常温西红柿(果蒂朝下熟透中)、洋葱土豆避光透气果蔬筐"},
                ],
            },
        ],
        "inventory_rules": "高频开封调味品必须冷藏；厨房零食抽屉柜按大人与儿童科学分层，避光防潮；餐桌抽纸余量低于1包时联动西卧备货仓取用。",
    },
    "东卧书房": {
        "name": "🖥️ 东卧·独立书房 (East Study / Workstation)",
        "english_name": "East Study & Workstation",
        "japanese_name": "東寝室・書斎ワークスペース",
        "zone_type": "深度办公学习与数码资产区",
        "family_function": "夫妻居家办公、远程视频会议、儿童学业辅导与数码设备维保",
        "furniture_layout": [
            {
                "piece": "1米北欧极简实木独立书桌 + 人体工学办公转椅",
                "sub_zones": [
                    {"level": "桌面右上角", "usage": "极简笔筒（书房文具剪刀、荧光笔、触控笔）、快充移动电源 20000mAh、无线鼠标垫"},
                    {"level": "桌面线缆理线槽", "usage": "65W 多口氮化镓充电头、Type-C 编织快充线、铝合金笔记本升降支架"},
                ],
            },
            {
                "piece": "桌下三层静音滑轨活动抽屉柜 (主抽屉柜)",
                "sub_zones": [
                    {"level": "第一层浅抽屉", "usage": "指甲刀套装(防飞溅款)、便签纸、回形针、加密U盘"},
                    {"level": "第二层中抽屉", "usage": "常用数码连接线、备用AA/AAA碱性电池、科学计算器"},
                    {"level": "第三层高抽屉", "usage": "一家三口重要证件袋、房产合同、家庭医疗保单、出生证明"},
                ],
            },
            {
                "piece": "独立多层办公辅抽屉柜 / 文件打印耗材柜 (主人选购筹备中)",
                "sub_zones": [
                    {"level": "第一层 (高频办公杂物与文具备用)", "usage": "备用中性笔芯、便利贴、手账贴纸、计算器、打孔器与印泥"},
                    {"level": "第二层 (数码摄影配件与外设耗材)", "usage": "移动硬盘、高速读卡器、多接口拓展坞、镜头清洁湿巾、各类备用转接头"},
                    {"level": "第三/四层 (A4打印纸与专业教材资料)", "usage": "整包 A4 打印复印纸 70g (500张整包)、风琴文件夹、夫妻专业书籍教材与档案盒"},
                ],
            },
            {
                "piece": "双层墙面胡桃木隔板置物架",
                "sub_zones": [
                    {"level": "下层随手格", "usage": "书房空调与顶灯遥控器（壁挂磁吸槽）、常用专业书籍与辞海"},
                    {"level": "上层展示格", "usage": "家庭温馨合影相框、头戴式无线降噪耳机、多肉盆栽"},
                ],
            },
        ],
        "inventory_rules": "桌下主抽屉柜收纳重要证件与指甲刀；新增辅抽屉柜专项归纳 A4 打印耗材、备用文具与数码外设，实现台面极致清爽与高能办公。",
    },
    "中卧主卧": {
        "name": "🗄️ 中卧·起居主卧 (Master Bedroom & Oshiire)",
        "english_name": "Master Bedroom & Oshiire",
        "japanese_name": "主寝室・押入れクローゼット",
        "zone_type": "主卧就寝与核心衣物被褥收纳区",
        "family_function": "夫妻主卧休息就寝、家庭换季衣物大件与家庭安全医药集中收纳",
        "furniture_layout": [
            {
                "piece": "1.8米实木双人主卧大床 + 软包床头 + 两侧超窄悬空床头几",
                "sub_zones": [
                    {"level": "床头左侧悬空柜", "usage": "温湿度计、护手霜、真丝睡眠眼罩、睡前读物"},
                    {"level": "床头右侧随手抽屉盒", "usage": "中卧空调与顶灯遥控器、磁吸手机充电线"},
                ],
            },
            {
                "piece": "经典和式大容量押入壁橱 (Oshiire - 双层深进深推拉门设计)",
                "sub_zones": [
                    {"level": "【上层·天袋 Tenbukuro】", "usage": "28寸铝镁合金空行李箱、20寸登机箱、家庭五金零件与多功能工具螺丝箱（极低频，高处安全储存）"},
                    {"level": "【中层·挂衣区与多功能隔板】", "usage": "防尘袋外套西装、当季大衣、专用家庭避光小药箱（布洛芬缓释胶囊12粒、医用无菌创口贴、碘伏消毒棉棒、耳温枪）"},
                    {"level": "【中层·内侧壁阻尼抽拉旋转全身镜】", "usage": "120cm×35cm 阻尼滑轨旋转全身镜（移门拉开后向外滑出旋转90°试衣照镜，用毕推回壁橱；0占地不压移门滑轨，杜绝夜间对床反光，完美解决主卧无镜痛点）"},
                    {"level": "【下层·抽屉式透明塑料收纳柜组】", "usage": "三组并排深抽屉箱，分类收纳夫妻二人换季贴身衣物、备用纯棉床单枕套、轻薄夏凉被"},
                ],
            },
            {
                "piece": "主卧角落 360° 旋转衣帽架全身穿衣镜 (兼次净衣收纳 · 备选柔性方案)",
                "sub_zones": [
                    {"level": "正面高清全身镜", "usage": "夫妻日常更衣、出门前全身仪容仪表整理检视"},
                    {"level": "背面实木衣帽挂架", "usage": "夫妻隔夜次净睡衣、家居服悬挂（睡前将镜面顺势旋转朝向墙面，彻底消除起夜反光）"},
                ],
            },
        ],
        "inventory_rules": "家庭医药箱集中在中层避光干燥处远离幼儿；押入移门严禁粘贴镜面防脱轨卡顿；主卧镜面选用押入内壁抽拉旋转镜或角落旋转衣帽镜，避开对床反光。",
    },
    "西卧储物间": {
        "name": "📦 西卧·儿童房与储物备货区 (West Room - Kids & Storage Hub)",
        "english_name": "West Bedroom (Kids & Storage Hub)",
        "japanese_name": "西部屋・子供部屋＆ストック倉庫",
        "zone_type": "儿童成长空间与家庭大宗物资战略备货仓",
        "family_function": "孩子独立成长游戏、家庭高频日用品大宗囤货、大件换季寝具与闲置家电封存",
        "furniture_layout": [
            {
                "piece": "儿童成长单人床 + 玩具图书分类矮柜",
                "sub_zones": [
                    {"level": "矮柜上层分类布盒", "usage": "儿童拼图积木、益智玩具、精装绘本图书"},
                    {"level": "床底滚轮防尘储物箱", "usage": "儿童换季衣物、保暖纯棉睡袋"},
                ],
            },
            {
                "piece": "独立封闭式四门大衣柜 (家庭大宗战略备货中枢)",
                "sub_zones": [
                    {"level": "【平开双门内侧·隐形防爆全身穿衣镜】", "usage": "120cm×30cm 无框超薄防爆全身镜（贴于平开柜门内侧，开门试衣照镜，关门彻底隐形，儿童房完全防撞防碎）"},
                    {"level": "【衣柜最上层·封闭隔层】", "usage": "闲置备用落地电风扇（套防尘保护罩）、客用加厚保暖羽绒棉被1床、备用换季被芯"},
                    {"level": "【衣柜中层·悬挂与叠放区】", "usage": "儿童羽绒服、厚外套、待熨烫换洗衣物"},
                    {"level": "【衣柜最下层·大宗物资备货战略区】", "usage": "整箱原木抽纸囤货（整箱12包装备用）、浓缩去油洗洁精(大容量补充装1kg)、蓝月亮洗衣液补充装(2kg*2)、优质五常大米(5kg未拆封)"},
                ],
            },
        ],
        "inventory_rules": "家庭战略物资总仓！大宗日用储备充足；平开柜门内侧防爆全身镜定期无水酒精擦拭保养；各房间物资触底先自此调拨。",
    },
    "洗面所与阳台": {
        "name": "🚿 洗面所、卫浴与家政阳台 (Washroom, Bath & Balcony)",
        "english_name": "Washroom, Bath & Balcony",
        "japanese_name": "洗面所・浴室＆ランドリーバルコニー",
        "zone_type": "全家洗漱、卫浴清洁与家政洗晒区",
        "family_function": "一家三口早晚清洁、全家衣物洗护烘干与清洁耗材收纳",
        "furniture_layout": [
            {
                "piece": "智能三门镜柜 + 洗手台一体式浴室柜",
                "sub_zones": [
                    {"level": "智能镜柜中间隔层", "usage": "电动牙刷替换刷头(4支装)、儿童防蛀牙膏、护肤水乳、牙线盒、棉签化妆棉"},
                    {"level": "洗手台下方防水柜", "usage": "备用洗手液补充袋、管道疏通剂、次氯酸消毒喷雾"},
                ],
            },
            {
                "piece": "阳台全铝洗衣机一体组合柜",
                "sub_zones": [
                    {"level": "洗衣机台面置物格", "usage": "蓝月亮除菌洗衣液(在用2包)、衣物柔顺剂、除菌留香珠"},
                    {"level": "侧边窄缝收纳推车", "usage": "晾衣架20只、被夹、防风夹、脏衣分类篮"},
                ],
            },
        ],
        "inventory_rules": "洗涤剂常备2包在用，用完1包触发西卧备货仓补给；卫浴化学品高处镜柜存放，杜绝儿童触碰。",
    },
}


def get_room_furniture_layout(room_name: str = "") -> Dict[str, Any]:
    """查询 3LDK 各房间的家具安排、收纳层级（如押入天袋/中层/下层）与动线规则。

    Args:
        room_name: 房间名称关键词，如'玄关'、'LDK'、'客厅'、'书房'、'主卧'、'西卧'、'储物'、'阳台'。
                   若为空，则返回全屋所有房间的家具布局总览。

    Returns:
        包含指定房间或全屋的家具配置清单、各家具内部细分收纳格、存放用途与当前房间内的实际物品列表。
    """
    items = _load_data()
    q = room_name.strip().lower()

    # Find matching rooms
    matched_rooms = {}
    for key, room_info in ROOM_FURNITURE_DIRECTORY.items():
        if (
            not q
            or q in key.lower()
            or q in room_info["name"].lower()
            or q in room_info.get("english_name", "").lower()
            or q in room_info.get("japanese_name", "").lower()
        ):
            # Attach current live items located in this room
            room_items = [
                it for it in items
                if any(k in it.get("location", "") for k in [key, room_info.get("japanese_name", ""), room_info.get("english_name", "")])
            ]
            info_copy = dict(room_info)
            info_copy["current_items_count"] = len(room_items)
            info_copy["current_items"] = [
                {
                    "name": it.get("name"),
                    "quantity": f"{it.get('quantity')} {it.get('unit', '')}",
                    "location": it.get("location"),
                    "notes": it.get("notes", ""),
                }
                for it in room_items
            ]
            matched_rooms[key] = info_copy

    if not matched_rooms:
        return {
            "status": "not_found",
            "message": f"未找到与 '{room_name}' 匹配的 3LDK 房间。可选房间：玄关、LDK客餐厨、东卧书房、中卧主卧、西卧储物间、洗面所与阳台。",
            "available_rooms": list(ROOM_FURNITURE_DIRECTORY.keys()),
        }

    return {
        "status": "success",
        "matched_count": len(matched_rooms),
        "rooms": matched_rooms,
    }


def compare_in_use_vs_backup_stock() -> Dict[str, Any]:
    """对比各房间正在使用的日常消耗品与西卧封闭衣柜储物间的战略备货储备，避免盲目重复采购。

    Returns:
        按物品对比在用位置余量与西卧备货仓库存，并提供针对性的内部调拨或外购建议。
    """
    items = _load_data()

    # Define linked consumable pairs: in-use keyword -> backup keyword
    linkages = [
        {"item_name": "原木抽纸", "in_use_loc": "LDK客餐厨", "backup_loc": "西卧储物间"},
        {"item_name": "浓缩去油洗洁精", "in_use_loc": "LDK客餐厨", "backup_loc": "西卧储物间"},
        {"item_name": "蓝月亮洗衣液", "in_use_loc": "洗面所与阳台", "backup_loc": "西卧储物间"},
        {"item_name": "电风扇", "in_use_loc": "LDK客餐厨", "backup_loc": "西卧储物间"},
    ]

    comparisons = []
    for link in linkages:
        name = link["item_name"]
        in_use_items = [it for it in items if name in it.get("name", "") and "在用" in it.get("notes", "") or (name in it.get("name", "") and "在用" in it.get("name", ""))]
        backup_items = [it for it in items if name in it.get("name", "") and ("备货" in it.get("name", "") or "补充" in it.get("name", "") or "备用" in it.get("name", "") or "闲置" in it.get("name", ""))]

        in_use_str = ", ".join([f"{it['name']} ({it['quantity']} {it['unit']}) 位于 {it['location']}" for it in in_use_items]) if in_use_items else "暂无在用记录"
        backup_str = ", ".join([f"{it['name']} ({it['quantity']} {it['unit']}) 位于 {it['location']}" for it in backup_items]) if backup_items else "西卧备货仓无备用库存"

        advice = "在用充足，备货稳健"
        if in_use_items and any(float(it.get("quantity", 0)) <= float(it.get("min_threshold", 1)) for it in in_use_items):
            if backup_items and any(float(it.get("quantity", 0)) > 0 for it in backup_items):
                advice = "⚠️ 在用触底！但西卧备货仓有充足囤货，直接从西卧大衣柜下层取用调拨即可，无需外购！"
            else:
                advice = "🚨 在用与备货均见底！需要立即加入家庭外购采购清单！"

        comparisons.append({
            "item_category": name,
            "in_use_status": in_use_str,
            "backup_storage_status": backup_str,
            "butler_recommendation": advice,
        })

    return {
        "status": "success",
        "description": "3LDK 三口之家在用物品 vs 西卧储物备货仓对比报告",
        "comparisons": comparisons,
        "golden_rule": "三口之家收纳铁律：日用耗材高频在用（少量便携）+ 西卧大宗备货（整箱集约），用完先调拨后采购，防止物品散乱堆积。",
    }
