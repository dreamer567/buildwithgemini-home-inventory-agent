"""Unit tests for Firestore inventory tools and memory callback."""

import pytest
from app.agent import generate_memories_callback, root_agent
from app.firestore_tools import (
    generate_replenishment_shopping_list,
    query_inventory_from_firestore,
    record_or_update_inventory_item,
)


def test_agent_tools_and_callbacks_configured():
    tool_names = [getattr(t, "__name__", t.__class__.__name__) for t in root_agent.tools]
    assert "PreloadMemoryTool" in tool_names
    assert "query_inventory_from_firestore" in tool_names
    assert "record_or_update_inventory_item" in tool_names
    assert "generate_replenishment_shopping_list" in tool_names
    assert "generate_item_image" in tool_names
    assert "generate_item_video" in tool_names
    assert "get_room_furniture_layout" in tool_names
    assert "compare_in_use_vs_backup_stock" in tool_names
    assert root_agent.code_executor is not None
    assert root_agent.after_agent_callback is generate_memories_callback


def test_query_inventory_from_firestore():
    res = query_inventory_from_firestore(search_term="剪刀")
    assert res["status"] == "success"
    assert res["total_matched"] >= 1
    assert any("剪刀" in it["name"] for it in res["items"])


def test_generate_replenishment_shopping_list():
    res = generate_replenishment_shopping_list(urgent_only=True)
    assert res["status"] == "success"
    assert "items" in res
    assert "markdown_checklist" in res
    assert res["total_to_buy"] >= 1
    assert "- [ ]" in res["markdown_checklist"]


@pytest.mark.asyncio
async def test_image_tool_signature_and_gcs():
    from app.image_tool import BUCKET_NAME, PROJECT_ID, generate_item_image
    assert BUCKET_NAME == "home-inventory-assets-0e1a68c8e387"
    assert PROJECT_ID == "qwiklabs-gcp-04-0e1a68c8e387"
    assert callable(generate_item_image)


@pytest.mark.asyncio
async def test_video_tool_signature_and_gcs():
    from app.video_tool import BUCKET_NAME, PROJECT_ID, OMNI_MODEL, generate_item_video
    assert BUCKET_NAME == "home-inventory-assets-0e1a68c8e387"
    assert PROJECT_ID == "qwiklabs-gcp-04-0e1a68c8e387"
    assert OMNI_MODEL == "gemini-omni-flash-preview"
    assert callable(generate_item_video)


