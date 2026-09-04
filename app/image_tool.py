"""Image generation tool using gemini-3.1-flash-lite-image in global region.

Saves the generated image as a session artifact and uploads to the public GCS bucket.
"""

import os
import re
from datetime import datetime, timezone
from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-0e1a68c8e387")
BUCKET_NAME = os.environ.get("HOME_INVENTORY_BUCKET", "home-inventory-assets-0e1a68c8e387")
IMAGE_MODEL = "gemini-3.1-flash-lite-image"
IMAGE_REGION = "global"


async def generate_item_image(
    item_name: str,
    prompt: str = "",
    tool_context: ToolContext | None = None,
) -> dict:
    """Generate a photo or visual card for an inventory item or storage space.

    Uses gemini-3.1-flash-lite-image in the global region. The generated image
    is saved as a session artifact and uploaded directly to public Cloud Storage.

    Args:
        item_name: Name of the item or area (e.g. '西红柿', '剪刀', '卧室二押入壁橱').
        prompt: Optional specific visual description or styling instruction.
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dict containing status, public image URL, and artifact details.
    """
    clean_name = item_name.strip()
    safe_slug = re.sub(r"[^\w\-]", "_", clean_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_slug}_{timestamp}.jpg"

    if prompt.strip():
        image_prompt = (
            f"A clean, minimal, aesthetic lifestyle photograph of {clean_name}: "
            f"{prompt.strip()}."
        )
    else:
        image_prompt = (
            f"A clean, aesthetic, high-quality photograph of {clean_name} "
            f"in a neat modern Japanese 3LDK home interior, soft daylight, realistic."
        )

    # 1. Generate image using gemini-3.1-flash-lite-image in global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=IMAGE_REGION)
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[image_prompt],
        config=types.GenerateContentConfig(
            response_modalities=[types.Modality.TEXT, types.Modality.IMAGE]
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"

    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {
            "status": "error",
            "message": f"No image was generated for '{item_name}'.",
        }

    # 2. Save artifact to Playground via tool_context.save_artifact
    version = None
    if tool_context is not None:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        version = await tool_context.save_artifact(filename=filename, artifact=part)

    # 3. Upload bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"items/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "item_name": item_name,
        "artifact_filename": filename,
        "artifact_version": version,
        "public_url": public_url,
        "message": f"Generated image for '{item_name}', saved to artifacts, and uploaded to {public_url}",
    }
