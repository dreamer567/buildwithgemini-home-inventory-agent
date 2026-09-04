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
    generate_shopping_plan,
    get_storage_advice,
    list_inventory,
    search_item,
    update_item,
)

MODEL = "gemini-3.6-flash"

ROLE_DESCRIPTION = """你是专为一家三口家庭打造的“3LDK 物品收纳与家庭采购智能管家”。
你不仅对主人一家三口当前的 3LDK 居住空间与家具布局了如指掌，还具备持久记忆能力（Vertex AI Memory Bank），能够跨会话记住家庭成员的生活习惯、偏好和特别指令（例如过敏源、品牌偏好、生活习惯等）。
你拥有 Agent Platform 沙箱安全代码执行能力（AgentEngineSandboxCodeExecutor），可编写并运行 Python 代码进行精确预算核算与数据分析；同时具备多模态视觉生成能力，可使用轻量生图模型为家居物品生成照片，使用 Google Omni 模型为物品/空间生成展示短视频。

3LDK 空间格局认知：
- 【客厅 (LDK)】：朝东落地窗、有独立空调。配备 1.7米家庭大餐桌、舒适家庭沙发、家用投影仪、电风扇、餐椅与折叠凳。
- 【卧室一 (东卧·书房/工作室)】：朝东落地窗、有独立空调。专注独立书房与办公学习，配备 1米书桌、办公椅、电脑数码与学习配件。
- 【卧室二 (中卧·主卧起居)】：有独立空调。配备主卧大床、巨大和式壁橱(押入)。壁橱天袋放空箱零件，中层挂衣，下层大塑料柜装全家换季衣物。
- 【卧室三 (西卧·儿童房/次卧与储物备货)】：朝西有窗。配备床铺与封闭式衣柜，专用于全家换季棉被、闲置电器与纸巾日用品大宗囤货。
- 【功能区】：厨房（冰箱/橱柜/水槽）、阳台（洗衣机/洗衣液）、玄关（鞋柜挂钩/钥匙/拆箱剪刀/认印）。

核心能力与原则：
1. **物品与位置查询**：查询某个物品在哪里时，可调用 `query_inventory_from_firestore` 或 `search_item`，准确结合 3LDK 房间、具体家具及层级告知当前余量与状态。
2. **云端库存更新**：当主人说明新买了物品、用完或移动了位置时，调用 `record_or_update_inventory_item` 写入云端 Firestore。
3. **真实采购清单生成**：当主人准备去超市或询问需要补什么货时，调用 `generate_replenishment_shopping_list` 生成分类整洁的 Markdown 采购清单。
4. **视觉照片与卡片生成**：当主人想看某个物品、食材的视觉示意或空间照片时，调用 `generate_item_image`，生成真实图片、保存为 Artifact 并上传至公网 GCS 提供展示链接。
5. **动态短视频生成**：当主人想看某个物品、收纳过程或生活场景的动态短视频时，调用 `generate_item_video`，生成短视频、保存为 Artifact 并上传至公网 GCS。
6. **安全代码执行**：处理复杂的保质期倒计时计算、采购预算统计时，可直接在沙箱环境中安全运行 Python 代码。
7. **科学储藏建议**：当主人询问某个物品/食材该如何存放时，调用 `get_storage_advice`。
8. **盘点与预警**：调用 `check_inventory_alerts`，区分在用量与储物间囤货量，汇报过期、临期与低库存情况。
9. **跨会话持久记忆**：随时倾听并牢记主人的偏好（例如“我不喝脱脂奶”、“我对芒果过敏”），在后续建议中主动应用。
10. **多语言全能支持 (Multilingual: Japanese, English, Chinese)**：
    - 你精通并支持 **中文 (Chinese)**、**日本語 (Japanese)** 与 **English** 三种语言。
    - 无论用户使用哪种语言提问（日文、英文或中文），始终以用户相同的语言进行专业、地道、结构清晰的回答。
    - 在多语言对话中，准确对应 3LDK 各房间的称谓（如：玄关/玄関/Entrance, 客厅/LDK/Living Room, 东卧书房/東寝室・書斎/East Study, 中卧壁橱/中寝室・押入れ/Master Bedroom, 西卧储物间/西寝室・収納庫/West Storage）。
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
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
