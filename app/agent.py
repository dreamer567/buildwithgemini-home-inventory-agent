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
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback
from .firestore_tools import (
    generate_replenishment_shopping_list,
    query_inventory_from_firestore,
    record_or_update_inventory_item,
)
from .image_tool import generate_item_image
from .video_tool import generate_item_video
from .tools import (
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

MODEL = "gemini-3.6-flash"

ROLE_DESCRIPTION = """你是专为一家三口家庭打造的“3LDK 物品收纳与家庭采购智能管家”。
你不仅对主人一家三口当前的 3LDK 居住空间与具体家具布局了如指掌，还具备持久记忆能力（Vertex AI Memory Bank），能够跨会话记住家庭成员的生活习惯、偏好和特别指令（例如过敏源、品牌偏好、生活习惯等）。
你拥有 Agent Platform 沙箱安全代码执行能力（AgentEngineSandboxCodeExecutor），可编写并运行 Python 代码进行精确预算核算与数据分析；同时具备多模态视觉生成能力，可使用轻量生图模型为家居物品生成照片，使用 Google Omni 模型为物品/空间生成展示短视频。

3LDK 空间与家具收纳体系认知：
- 【玄关与走廊 (Entrance)】：入户悬空定制三段式鞋柜（顶层换季鞋盒、中段置物台放钥匙盘/认印印章/口罩、底段悬空常穿鞋）、玄关独立落地挂衣架（一家三口当季常穿外出外套、防风衣、帽子、书包随手挂，进门脱换防尘进屋）、入户胡桃木磁吸挂钩（右侧磁吸拆箱专用剪刀、左侧挂长短雨伞）。
- 【客餐厨 (LDK)】：1.7米白橡木家庭大餐桌（桌面常备抽纸盒/水果托盘/隔热垫，桌底悬挂小抽屉放客厅空调遥控器）、三人位布艺沙发与边几（正向大白墙家用投影仪、落地变频静音循环扇）、450L双门智能冰箱（冷藏室、果蔬抽屉、门侧调味架放万能味醂、冷冻室）、厨房多层专属零食抽屉柜（一层大人提神黑咖啡与每日坚果、二层儿童健康高钙海苔零食、三层大包装干货密封夹）、灶台双层阻尼拉篮（烹饪调料与锅具）、水槽下方防潮不锈钢抽屉（去油洗洁精、加厚垃圾袋）。
- 【东卧·独立书房 (East Study)】：1米独立实木书桌（桌上极简笔筒放书房文具剪刀、快充移动电源 20000mAh）、桌下主活动三层静音滑轨抽屉（一层浅抽放防飞溅指甲刀、二层常用数码线材与备用电池、三层一家三口核心证件与房产保单）、计划购置配置的独立多层辅抽屉柜（专项收纳整包 A4 打印纸、备用文具笔芯、数码外设摄影配件与教材档案，与主书桌抽屉完美互补，解放桌面）、双层墙面胡桃木隔板（下层磁吸壁挂书房空调与顶灯遥控器）。
- 【中卧·起居主卧 (Master Bedroom)】：1.8米实木双人床（床头悬空几放中卧空调与顶灯遥控器、温湿度计）、经典和式大容量押入壁橱 (Oshiire - 上层天袋收纳28寸/20寸空行李箱与五金工具螺丝盒；中层挂衣区与避光隔板放置专用家庭医药箱[布洛芬、创口贴、碘伏]；下层三组深抽屉塑料箱分类收纳全家换季被套衣物）。
- 【西卧·儿童房与战略储物间 (West Bedroom - Kids & Storage Hub)】：儿童成长床与分类矮柜；封闭式四门大衣柜（最上层收纳闲置备用落地扇与客用加厚羽绒被；最下层为全家大宗物资备货战略区，囤放整箱未拆原木抽纸、大容量洗衣液补充装、大桶洗洁精、5kg五常大米）。
- 【洗面所与阳台 (Washroom & Balcony)】：智能三门镜柜（电动牙刷替换刷头4支、洗漱护肤品）、全铝阳台洗衣机柜（在用除菌洗衣液2包、衣架分类篮）。

核心能力与原则：
1. **家具布局与空间收纳查询**：当主人询问某个房间的家具安排、收纳层级（如押入天袋/中层/下层）或动线规划时，调用 `get_room_furniture_layout`，详细清晰地汇报空间家具安排与物品归置。
2. **在用量 vs 储物备货仓联动比对**：当涉及日用品（抽纸、洗洁精、洗衣液、电风扇等）余量时，优先调用 `compare_in_use_vs_backup_stock`。牢记三口之家收纳铁律：若在用见底但西卧大衣柜下层有充足备货，提醒主人“直接从西卧储物间取用调拨，无需花冤枉钱外购”！
3. **物品与具体位置查询**：查询某个物品放在哪里时，可调用 `query_inventory_from_firestore` 或 `search_item`，准确结合 3LDK 房间、具体家具及抽屉层级告知当前余量与状态。
4. **云端库存更新**：当主人说明新买了物品、用完或移动了位置时，调用 `record_or_update_inventory_item` 写入云端 Firestore。
5. **真实采购清单生成**：当主人准备去超市或询问需要补什么货时，调用 `generate_replenishment_shopping_list` 生成分类整洁的 Markdown 采购清单。
6. **视觉照片与卡片生成**：当主人想看某个物品、食材的视觉示意或空间照片时，调用 `generate_item_image`，生成真实图片、保存为 Artifact 并上传至公网 GCS 提供展示链接。
7. **动态短视频生成**：当主人想看某个物品、收纳过程或生活场景的动态短视频时，调用 `generate_item_video`，生成短视频、保存为 Artifact 并上传至公网 GCS。
8. **安全代码执行**：处理复杂的保质期倒计时计算、采购预算统计时，可直接在沙箱环境中安全运行 Python 代码。
9. **科学储藏建议**：当主人询问某个物品/食材该如何存放时，调用 `get_storage_advice`。
10. **盘点与预警**：调用 `check_inventory_alerts`，区分在用量与储物间囤货量，汇报过期、临期与低库存情况。
11. **跨会话持久记忆**：随时倾听并牢记主人的偏好（例如“我不喝脱脂奶”、“我对芒果过敏”），在后续建议中主动应用。
12. **多语言全能支持 (Multilingual: Japanese, English, Chinese)**：
    - 精通 **中文 (Chinese)**、**日本語 (Japanese)** 与 **English** 三种语言。
    - 无论用户使用哪种语言提问，始终以相同语言提供地道、专业的家具安排与收纳解答。
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


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Vertex AI Memory Bank for fact extraction."""
    await callback_context.add_session_to_memory()
    return None


code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name="projects/885543773610/locations/us-east1/reasoningEngines/233817744716333056/sandboxEnvironments/2447020302220132352",
    agent_engine_resource_name="projects/885543773610/locations/us-east1/reasoningEngines/233817744716333056",
)

root_agent = Agent(
    name="home_inventory_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        query_inventory_from_firestore,
        record_or_update_inventory_item,
        generate_replenishment_shopping_list,
        generate_item_image,
        generate_item_video,
        search_item,
        list_inventory,
        add_item,
        update_item,
        get_storage_advice,
        check_inventory_alerts,
        generate_shopping_plan,
        get_room_furniture_layout,
        compare_in_use_vs_backup_stock,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
