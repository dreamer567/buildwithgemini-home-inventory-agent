# My agent: home-inventory-agent
One-liner: A conversational agent that helps solo dwellers manage household assets, grocery freshness, and shopping replenishment with a catalog of 3LDK home items and pantry stock.

Tool coverage:
- Memory: User's 3LDK layout (east-facing study with 1m desk, middle dark bedroom with oshiire closet, west storage room, east-facing living room with AC/projector), personal habits (placing scissors at entrance and desk, remote controls inside oshiire edge to eliminate bedside chairs, personal seal on entrance shoe cabinet), consumption habits, and dietary preferences.
- Tools: Inventory lookups and management (search_item, add_item, update_item), scientific food/asset preservation advice (get_storage_advice), expiry & stock shortage audit (check_inventory_alerts), and automated solo-living replenishment plan generation (generate_shopping_plan).
- Catalog/UI: Visual item detail cards (location badges, quantities, categories), color-coded expiry and low-stock warning tables (🔴 expired, 🟡 expiring soon, ⚠️ low stock), and categorized shopping checklist cards rendered via A2UI.
- Image gen: Storage visualization diagrams (e.g. recommended refrigerator partition layout or oshiire closet multi-tier shelving schematic) and visual suggestions for using up expiring food ingredients.
- Sandbox: Dynamic shelf-life remaining days calculation, consumption rate estimations, grocery budget totals, and household volume optimization.

Core rails (everyone): memory, tools, eval, deploy, frontend
My stretch menu (pick later): A2UI (rich display cards and alert tables), Vertex AI Memory Bank (long-term multi-session preference persistence), Code Sandbox (shelf-life & grocery budget computation)
First eval question: "我后天要去超市采购，帮我检查一下冰箱和储物间，生成一份紧急程度明确的独居采购计划，并提醒我哪些食材必须先吃完。"
