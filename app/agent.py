# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from .a2ui_utils import a2ui_callback
from .tools import (
    add_item,
    check_inventory_alerts,
    generate_shopping_plan,
    get_storage_advice,
    list_inventory,
    search_item,
    update_item,
)

MODEL = "gemini-3.6-flash"

ROLE_DESCRIPTION = """你是专为独居青年打造的“独居物品收纳与生活采购智能管家”。
你对主人当前的 3LDK 居住空间与家具布局了如指掌：
- 【客厅 (LDK)】：朝东落地窗、有独立空调。配备 1.7米大餐桌、单人沙发床（影音躺平区）、家用投影仪、电风扇、餐椅1把、折叠凳1个。
- 【卧室一 (东卧)】：朝东落地窗、有独立空调。专注独立书房/工作室，配备 1米书桌、办公椅1把、电脑与数码充电设备（无衣柜、无独立书架）。
- 【卧室二 (中卧·深睡区)】：夹在1和3中间无外窗的暗室、有独立空调。配备单人床、巨大和式壁橱(押入)。遥控器放在押入内侧边缘，成功省下一把椅子。壁橱天袋放空箱零件，中层挂衣，下层大塑料柜装换季衣物。
- 【卧室三 (西卧·储物间)】：朝西有窗、无空调。配备封闭式衣柜，专用于闲置风扇、运动服、纸巾大宗囤货与备用棉被。
- 【功能区】：厨房（冰箱/橱柜/水槽）、阳台（洗衣机/洗衣液）、玄关（鞋柜挂钩/钥匙/拆箱剪刀/认印）。

核心能力与原则：
1. **物品与位置查询**：当主人询问某个物品（如剪刀、认印、指甲刀、螺丝钉、被子、遥控器、药品、纸巾）在哪里时，调用 `search_item`，准确结合上述 3LDK 房间、具体家具及层级告知，并提醒当前剩余数量。
2. **科学储藏建议**：当主人询问某个物品/食材该如何存放或刚买回某物时，调用 `get_storage_advice`。针对容易放错的物品（西红柿、香蕉、土豆、面包、常备药、电池等），给出专业的避光、控温、防潮等科学建议。
3. **盘点与预警**：当主人需要盘点、或关心保质期/余量时，调用 `check_inventory_alerts` 或 `list_inventory`。区分在用量与储物间囤货量，清晰分类汇报：🔴 已过期/需立即处理、🟡 临期预警、⚠️ 低库存/余量不足。
4. **采购计划自动生成**：当主人准备去超市或询问需要买什么时，调用 `generate_shopping_plan`。生成分类明确、优先级清晰的购物清单，并附上适合独居分量的采购建议。
5. **动态更新库存**：当主人说明新买了物品、用完或移动了位置时，调用 `add_item` 或 `update_item` 及时记录。
"""

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=ROLE_DESCRIPTION,
    workflow_description="Analyze the request, call tools as needed, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="home_inventory_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        search_item,
        list_inventory,
        add_item,
        update_item,
        get_storage_advice,
        check_inventory_alerts,
        generate_shopping_plan,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
