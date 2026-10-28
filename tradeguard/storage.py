"""截图压缩与旧版 base64 证据解码。"""

from __future__ import annotations

import base64
import io
import re

from PIL import Image, ImageOps

from .config import MAX_IMAGE_BYTES

DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)


class ImageError(ValueError):
    """用户上传的图片无法处理。"""


def decode_data_url(value: str) -> tuple[bytes, str]:
    match = DATA_URL_RE.match((value or "").strip())
    if not match:
        raise ImageError("不是合法的图片 data URL")
    try:
        raw = base64.b64decode(match.group(2), validate=False)
    except Exception as exc:  # noqa: BLE001
        raise ImageError("图片 base64 解码失败") from exc
    return raw, match.group(1)


def compress_image(raw: bytes, *, max_dimension: int = 1600, quality: int = 85) -> tuple[bytes, str]:
    """压缩截图为 JPEG，并限制长边，避免数据库被原图撑爆。"""
    if not raw:
        raise ImageError("图片内容为空")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ImageError("图片超过单张大小限制")

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as exc:  # noqa: BLE001
        raise ImageError("图片格式无法识别") from exc

    image = ImageOps.exif_transpose(image)

    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue(), "image/jpeg"
