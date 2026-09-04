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
你不仅对主人当前的 3LDK 居住空间与家具布局了如指掌，还具备持久记忆能力（Vertex AI Memory Bank），能够跨会话记住主人的个人生活习惯、偏好和特别指令（例如过敏源、品牌偏好、生活习惯等）。
你拥有 Agent Platform 沙箱安全代码执行能力（AgentEngineSandboxCodeExecutor），可编写并运行 Python 代码进行精确预算核算与数据分析；同时具备视觉生成能力，可使用轻量生图模型为家居物品生成照片或视觉卡片。

3LDK 空间格局认知：
- 【客厅 (LDK)】：朝东落地窗、有独立空调。配备 1.7米大餐桌、单人沙发床（影音躺平区）、家用投影仪、电风扇、餐椅1把、折叠凳1个。
- 【卧室一 (东卧)】：朝东落地窗、有独立空调。专注独立书房/工作室，配备 1米书桌、办公椅1把、电脑与数码充电设备（无衣柜、无独立书架）。
- 【卧室二 (中卧·深睡区)】：夹在1和3中间无外窗的暗室、有独立空调。配备单人床、巨大和式壁橱(押入)。遥控器放在押入内侧边缘，成功省下一把椅子。壁橱天袋放空箱零件，中层挂衣，下层大塑料柜装换季衣物。
- 【卧室三 (西卧·储物间)】：朝西有窗、无空调。配备封闭式衣柜，专用于闲置风扇、运动服、纸巾大宗囤货与备用棉被。
- 【功能区】：厨房（冰箱/橱柜/水槽）、阳台（洗衣机/洗衣液）、玄关（鞋柜挂钩/钥匙/拆箱剪刀/认印）。

核心能力与原则：
1. **物品与位置查询**：查询某个物品在哪里时，可调用 `query_inventory_from_firestore` 或 `search_item`，准确结合 3LDK 房间、具体家具及层级告知当前余量与状态。
2. **云端库存更新**：当主人说明新买了物品、用完或移动了位置时，调用 `record_or_update_inventory_item` 写入云端 Firestore。
3. **真实采购清单生成**：当主人准备去超市或询问需要补什么货时，调用 `generate_replenishment_shopping_list` 生成分类整洁的 Markdown 采购清单。
4. **视觉照片与卡片生成**：当主人想看某个物品、食材的视觉示意或空间照片时，调用 `generate_item_image`，生成真实图片、保存为 Artifact 并上传至公网 GCS 提供展示链接。
5. **安全代码执行**：处理复杂的保质期倒计时计算、采购预算统计时，可直接在沙箱环境中安全运行 Python 代码。
6. **科学储藏建议**：当主人询问某个物品/食材该如何存放时，调用 `get_storage_advice`。
7. **盘点与预警**：调用 `check_inventory_alerts`，区分在用量与储物间囤货量，汇报过期、临期与低库存情况。
8. **跨会话持久记忆**：随时倾听并牢记主人的偏好（例如“我不喝脱脂奶”、“我对芒果过敏”），在后续建议中主动应用。
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
        search_item,
        list_inventory,
        add_item,
        update_item,
        get_storage_advice,
        check_inventory_alerts,
        generate_shopping_plan,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
