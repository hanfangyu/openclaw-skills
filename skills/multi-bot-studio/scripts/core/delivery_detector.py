from __future__ import annotations
import re
from typing import Dict

URL_RE = re.compile(r"https?://\S+", re.I)
VIDEO_HINT_RE = re.compile(r"\.(mp4|mov|m4v|webm)(\?|$)", re.I)
IMAGE_HINT_RE = re.compile(r"\.(png|jpg|jpeg|webp|gif)(\?|$)", re.I)
ASSET_ID_RE = re.compile(r"\b(asset_ids?|evl_[a-z0-9_\-]+)\b", re.I)


def detect_delivery(event: Dict) -> bool:
    if bool(event.get("has_delivery")):
        return True
    if int(event.get("media_count") or 0) > 0:
        return True
    text = str(event.get("text") or "")
    urls = URL_RE.findall(text)
    for u in urls:
        if VIDEO_HINT_RE.search(u) or IMAGE_HINT_RE.search(u):
            return True
        if any(host in u for host in ("files.evolink.ai", "media.evolink.ai", "cdn.discordapp.com")):
            return True
    # 兼容仅回传 asset_id 的阶段（如锚点图）
    if ASSET_ID_RE.search(text):
        return True
    return False


def normalize_event(event: Dict) -> Dict:
    out = dict(event)
    if out.get("type") == "role_update":
        role = out.get("role")
        if role == "editor":
            out["has_delivery"] = detect_delivery(out)
        elif role in ("writer", "director") and out.get("status") == "已完成":
            out["has_delivery"] = True
        elif role == "vfx" and out.get("status") == "已完成":
            out["has_delivery"] = detect_delivery(out)
    return out
