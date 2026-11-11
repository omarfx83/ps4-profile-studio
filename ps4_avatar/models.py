"""Small data models shared between the UI and services."""

import io
from dataclasses import dataclass, field

from PIL import Image

from .dds import SIZES


@dataclass
class User:
    uid: str
    name: str = ""
    online_id: str = ""
    thumb: Image.Image | None = None
    facts: dict = field(default_factory=dict)
    selected: bool = False

    @property
    def display_name(self):
        return self.name or f"User {self.uid}"


@dataclass
class AvatarSet:
    """Rendered avatar images, encoded DDS files and decoded previews."""

    images: dict[int, Image.Image]
    dds: dict[int, bytes]
    previews: dict[int, Image.Image]

    def png_bytes(self):
        buf = io.BytesIO()
        self.images[440].save(buf, "PNG")
        return buf.getvalue()

    def files(self, pictures=False):
        """Files ready to export or upload."""
        out = {f"avatar{size}.dds": self.dds[size] for size in SIZES}
        png = self.png_bytes()
        out["avatar440.png"] = png
        if pictures:
            for size in SIZES:
                out[f"picture{size}.dds"] = self.dds[size]
            out["picture.png"] = png
        return out
