"""Video generation tool using Google's Omni model (gemini-omni-flash-preview) in global region.

Saves the generated video as a session artifact and uploads directly to the public GCS bucket.
"""

import base64
import logging
import re
from datetime import datetime, timezone
from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

logger = logging.getLogger(__name__)

PROJECT_ID = "qwiklabs-gcp-04-0e1a68c8e387"
BUCKET_NAME = "home-inventory-assets-0e1a68c8e387"
OMNI_MODEL = "gemini-omni-flash-preview"
OMNI_REGION = "global"


async def generate_item_video(
    item_name: str,
    prompt: str = "",
    tool_context: ToolContext | None = None,
) -> dict:
    """Generate a short video for an inventory item or 3LDK home storage space.

    Uses Google's Omni model (gemini-omni-flash-preview) in the global region.
    The generated video is saved as a session artifact and uploaded directly
    to public Cloud Storage without writing to a local file.

    Args:
        item_name: Name of the item or area (e.g. '味醂', '玄关剪刀', '押入壁橱收纳盒').
        prompt: Optional specific motion or scene description for the video clip.
        tool_context: ADK ToolContext injected by the framework.

    Returns:
        A dict containing status, public video URL, and artifact details.
    """
    clean_name = item_name.strip()
    safe_slug = re.sub(r"[^\w\-]", "_", clean_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_slug}_{timestamp}.mp4"

    if prompt.strip():
        video_prompt = (
            f"A realistic cinematic short video of {clean_name}: {prompt.strip()}. "
            f"Smooth camera motion, 4k detail, clean lighting."
        )
    else:
        video_prompt = (
            f"A realistic aesthetic short video clip of {clean_name} inside a modern Japanese "
            f"3LDK apartment, showcasing its neat placement and use, smooth subtle camera glide, realistic lighting."
        )

    logger.info("Generating video with %s in %s: %s", OMNI_MODEL, OMNI_REGION, video_prompt)

    # 1. Generate video using gemini-omni-flash-preview in global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=OMNI_REGION)
    interaction = client.interactions.create(
        model=OMNI_MODEL,
        input=video_prompt,
    )

    video_bytes: bytes | None = None
    if hasattr(interaction, "output_video") and interaction.output_video:
        data = interaction.output_video.data
        if isinstance(data, str):
            video_bytes = base64.b64decode(data)
        elif isinstance(data, (bytes, bytearray)):
            video_bytes = bytes(data)

    if not video_bytes:
        logger.error("No video data returned from Omni interaction: %s", interaction)
        return {
            "status": "error",
            "message": f"No video was generated for '{item_name}'.",
        }

    # 2. Save artifact to Playground via tool_context.save_artifact
    version = None
    if tool_context is not None:
        part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        version = await tool_context.save_artifact(filename=filename, artifact=part)

    # 3. Upload bytes to public Cloud Storage bucket (no local file)
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"videos/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type="video/mp4")
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "item_name": item_name,
        "artifact_filename": filename,
        "artifact_version": version,
        "public_url": public_url,
        "message": f"Generated video for '{item_name}', saved to artifacts, and uploaded to {public_url}",
    }
