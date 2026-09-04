"""Firestore-backed inventory management and replenishment tools.

Hardcodes the GCP project ID string 'qwiklabs-gcp-04-0e1a68c8e387' to prevent
Agent Platform project-number resolution bugs.
"""

import os
from datetime import datetime, timezone
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-0e1a68c8e387")
COLLECTION_NAME = "inventory_items"


def get_firestore_client() -> firestore.Client:
    """Return a Firestore client initialized with the project ID."""
    proj = os.environ.get("GOOGLE_CLOUD_PROJECT") or PROJECT_ID
    return firestore.Client(project=proj)


def query_inventory_from_firestore(
    search_term: str = "", location: str = "", category: str = ""
) -> dict:
    """Query items from the Firestore cloud inventory.

    Args:
        search_term: Keyword to match against item name or notes (e.g. '剪刀', '牛奶', '遥控器').
        location: Keyword to filter by room or area (e.g. '玄关', '卧室一', '厨房', '客厅').
        category: Category filter (e.g. '食品蔬菜水果', '日用品', '资产与常备品').

    Returns:
        A dictionary containing matched items and their locations.
    """
    db = get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()

    matched = []
    search_term_lower = search_term.strip().lower()
    location_lower = location.strip().lower()
    category_lower = category.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        data["doc_id"] = doc.id

        # Location filter
        if location_lower and location_lower not in data.get("location", "").lower():
            continue

        # Category filter
        if category_lower and category_lower not in data.get("category", "").lower():
            continue

        # Search term filter
        if search_term_lower:
            name_match = search_term_lower in data.get("name", "").lower()
            notes_match = search_term_lower in data.get("notes", "").lower()
            loc_match = search_term_lower in data.get("location", "").lower()
            if not (name_match or notes_match or loc_match):
                continue

        matched.append({
            "id": data.get("id", doc.id),
            "name": data.get("name"),
            "category": data.get("category"),
            "location": data.get("location"),
            "quantity": f"{data.get('quantity', 1)} {data.get('unit', '')}".strip(),
            "expiry_date": data.get("expiry_date"),
            "notes": data.get("notes", ""),
        })

    return {
        "status": "success",
        "total_matched": len(matched),
        "items": matched,
    }


def record_or_update_inventory_item(
    name: str,
    location: str,
    category: str = "日用品",
    quantity: float = 1.0,
    unit: str = "个",
    expiry_date: str = "",
    min_threshold: float = 1.0,
    notes: str = "",
) -> dict:
    """Record a new item or update an existing item's location and quantity in Firestore.

    Args:
        name: Name of the item (e.g. '指甲刀', '抽纸').
        location: Specific storage location (e.g. '卧室一1米书桌抽屉', '玄关鞋柜上方挂钩').
        category: Category ('食品蔬菜水果', '日用品', '资产与常备品').
        quantity: Current count or amount.
        unit: Unit of measurement (e.g. '个', '瓶', '盒', '包', '把').
        expiry_date: Expiration date in YYYY-MM-DD format (if applicable).
        min_threshold: Safety stock threshold before triggering a restock alert.
        notes: Context, condition, or storage guidelines.

    Returns:
        A dictionary confirming the update in Firestore.
    """
    db = get_firestore_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Search for an existing document with the same name and location
    query = (
        db.collection(COLLECTION_NAME)
        .where("name", "==", name.strip())
        .limit(1)
        .stream()
    )
    existing_doc = next(query, None)

    if existing_doc:
        doc_ref = db.collection(COLLECTION_NAME).document(existing_doc.id)
        doc_data = {
            "name": name.strip(),
            "location": location.strip(),
            "category": category.strip(),
            "quantity": quantity,
            "unit": unit.strip(),
            "expiry_date": expiry_date.strip() if expiry_date else existing_doc.to_dict().get("expiry_date"),
            "min_threshold": min_threshold,
            "notes": notes.strip() if notes else existing_doc.to_dict().get("notes", ""),
            "updated_at": now_iso,
        }
        doc_ref.update(doc_data)
        doc_id = existing_doc.id
        action = "updated"
    else:
        # Create a new document with an auto-id or count
        doc_ref = db.collection(COLLECTION_NAME).document()
        doc_id = doc_ref.id
        doc_data = {
            "id": doc_id,
            "name": name.strip(),
            "location": location.strip(),
            "category": category.strip(),
            "quantity": quantity,
            "unit": unit.strip(),
            "expiry_date": expiry_date.strip() if expiry_date else None,
            "min_threshold": min_threshold,
            "notes": notes.strip(),
            "updated_at": now_iso,
        }
        doc_ref.set(doc_data)
        action = "created"

    return {
        "status": "success",
        "action": action,
        "doc_id": doc_id,
        "item": doc_data,
        "message": f"Successfully {action} '{name}' in Firestore inventory.",
    }


def generate_replenishment_shopping_list(urgent_only: bool = True) -> dict:
    """Generate an actionable shopping replenishment list from Firestore.

    Scans Firestore inventory for low-stock essentials (below minimum threshold)
    and items expiring in the next 3 days, grouping them into a clean checklist.

    Args:
        urgent_only: If True, only include critical low-stock and expiring items.
                     If False, includes general pantry refresh suggestions.

    Returns:
        A dictionary containing the categorized shopping list and total items count.
    """
    db = get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()

    now_date_str = datetime.now().strftime("%Y-%m-%d")

    shopping_items = []

    for doc in docs:
        item = doc.to_dict()
        qty = float(item.get("quantity", 0))
        min_thresh = float(item.get("min_threshold", 0))
        exp = item.get("expiry_date")

        is_low_stock = qty <= min_thresh
        is_expiring = False
        days_left = None

        if exp:
            try:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                now_dt = datetime.strptime(now_date_str, "%Y-%m-%d")
                delta = (exp_dt - now_dt).days
                if delta <= 3:
                    is_expiring = True
                    days_left = delta
            except ValueError:
                pass

        if is_low_stock or is_expiring or not urgent_only:
            reason = []
            if is_low_stock:
                reason.append(f"余量仅剩 {qty} {item.get('unit', '')} (警戒线: {min_thresh})")
            if is_expiring:
                if days_left is not None and days_left < 0:
                    reason.append(f"已过期 {-days_left} 天，需重新选购")
                elif days_left is not None:
                    reason.append(f"{days_left} 天后到期")

            shopping_items.append({
                "name": item.get("name"),
                "category": item.get("category", "日用品"),
                "current_quantity": f"{qty} {item.get('unit', '')}",
                "location": item.get("location"),
                "reason": "；".join(reason) if reason else "常备补充",
            })

    # Group by category
    categories: dict[str, list] = {}
    for it in shopping_items:
        cat = it["category"]
        categories.setdefault(cat, []).append(it)

    # Format Markdown checklist
    markdown_lines = ["### 🛒 3LDK 家庭生活补货采购清单\n"]
    for cat, items in categories.items():
        markdown_lines.append(f"#### 🏷️ {cat}")
        for it in items:
            markdown_lines.append(f"- [ ] **{it['name']}**（当前：{it['current_quantity']}）— *{it['reason']}*")
        markdown_lines.append("")

    checklist_md = "\n".join(markdown_lines).strip()

    return {
        "status": "success",
        "total_to_buy": len(shopping_items),
        "items": shopping_items,
        "markdown_checklist": checklist_md,
    }
