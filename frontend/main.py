"""FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import asyncio
import base64
import logging
import os
import uuid
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import TransportProtocol
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types as genai_types
from google.protobuf.json_format import MessageToDict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proxy")

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/885543773610/locations/us-east1/reasoningEngines/233817744716333056",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


def _analyze_image_sync(img_bytes: bytes, mime_type: str) -> str:
    """Analyze uploaded photo or receipt using Gemini 2.5 Flash on Vertex AI."""
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-0e1a68c8e387")
        client = genai.Client(vertexai=True, project=project_id, location=LOCATION)
        prompt = (
            "你是一个专业的 3LDK 家居物品与食材收纳识别助手。请仔细观察这张用户上传的照片"
            "（可能是超市购物小票、刚采购回来的生活物品包装、或家中某个角落的收纳实物）。"
            "请准确提取图中的所有具体物品名称、预估数量、包装规格以及能识别出的保质期/生产日期信息。"
            "用清晰精炼的中文条目列出识别到的物品。"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                genai_types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return f"(图片分析暂不可用: {e})"


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    logger.exception("Chat error: %s", exc)
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}


def _extract_part_dict(part: Any) -> dict | None:
    # Text part
    if getattr(part, "text", None):
        return {"kind": "text", "text": part.text}
    # URL / file link
    if getattr(part, "url", None):
        return {"kind": "text", "text": part.url}
    # A2UI / structured data part
    if hasattr(part, "HasField") and part.HasField("data"):
        data_dict = MessageToDict(part.data)
        if isinstance(data_dict, dict) and "data" in data_dict:
            inner = data_dict["data"]
            if isinstance(inner, dict) and (
                "beginRendering" in inner or "surfaceUpdate" in inner
            ):
                return {"kind": "a2ui", "data": inner}
        return {"kind": "a2ui", "data": data_dict}
    return None


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    image_base64 = body.get("image_base64")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    # Multimodal image handling
    if image_base64:
        mime_type = "image/jpeg"
        if "," in image_base64:
            header, b64_data = image_base64.split(",", 1)
            if "data:" in header and ";base64" in header:
                mime_type = header.replace("data:", "").split(";")[0]
        else:
            b64_data = image_base64

        try:
            img_bytes = base64.b64decode(b64_data)
            vision_result = await asyncio.to_thread(_analyze_image_sync, img_bytes, mime_type)
            if vision_result:
                user_msg = message.strip() if message else "请帮我将这些物品分类归置到 3LDK 对应房间的收纳位置，并记录保质期与库存状态。"
                message = (
                    f"【📷 实物/小票视觉识别结果】：\n{vision_result}\n\n"
                    f"【用户需求】：{user_msg}"
                )
        except Exception as e:
            logger.error(f"Failed to process image: {e}")

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as http_client:
        config = ClientConfig(
            httpx_client=http_client,
            supported_protocol_bindings=[
                TransportProtocol.JSONRPC,
                TransportProtocol.HTTP_JSON,
            ],
        )
        client = await create_client(A2A_BASE, config)

        context_id = _contexts.get(user_id, "")
        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text=message)],
            context_id=context_id,
        )

        async for chunk in client.send_message(SendMessageRequest(message=msg)):
            if chunk.HasField("artifact_update"):
                if chunk.artifact_update.context_id:
                    _contexts[user_id] = chunk.artifact_update.context_id
                for p in chunk.artifact_update.artifact.parts:
                    extracted = _extract_part_dict(p)
                    if extracted:
                        parts.append(extracted)
            elif chunk.HasField("task"):
                if chunk.task.context_id:
                    _contexts[user_id] = chunk.task.context_id
                for art in chunk.task.artifacts:
                    for p in art.parts:
                        extracted = _extract_part_dict(p)
                        if extracted:
                            parts.append(extracted)
            elif chunk.HasField("message"):
                if chunk.message.context_id:
                    _contexts[user_id] = chunk.message.context_id
                for p in chunk.message.parts:
                    extracted = _extract_part_dict(p)
                    if extracted:
                        parts.append(extracted)

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
