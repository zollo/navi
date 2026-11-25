"""Page look: background, content panel, font, text color, buttons and avatar.

Stored as JSON on the page (`pages.theme`) and saved with the rest of the page by
`PUT /api/pages/me`. Every field has a default, so `{}` is the default look, and
null colors mean "automatic": the page follows the viewer's light or dark mode, or
picks a readable color for the background.
"""
from __future__ import annotations

import enum
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

HEX_COLOR_LEN = 7  # "#rrggbb"


def _check_color(value: str) -> str:
    v = value.strip().lower()
    if len(v) != HEX_COLOR_LEN or v[0] != "#" or any(c not in "0123456789abcdef" for c in v[1:]):
        raise ValueError("must be a hex color like #1a2b3c")
    return v


Color = Annotated[str, AfterValidator(_check_color)]


class BackgroundKind(enum.StrEnum):
    default = "default"  # the standard page background (follows light/dark mode)
    solid = "solid"
    gradient = "gradient"
    image = "image"  # the page's own uploaded image
    curated = "curated"  # an image from the admin-curated gallery


class Font(enum.StrEnum):
    # Self-hosted in the SPA (Fontsource); keep in sync with frontend/src/lib/theme.ts.
    system = "system"
    inter = "inter"
    nunito = "nunito"
    lora = "lora"
    playfair = "playfair"
    space_mono = "space-mono"
    caveat = "caveat"


class ButtonStyle(enum.StrEnum):
    filled = "filled"
    outline = "outline"
    glass = "glass"  # translucent, blurs the background behind it
    shadow = "shadow"  # filled with a hard offset shadow


class ButtonShape(enum.StrEnum):
    square = "square"
    rounded = "rounded"
    pill = "pill"


class AvatarShape(enum.StrEnum):
    circle = "circle"
    rounded = "rounded"
    square = "square"


class ThemeBackground(BaseModel):
    kind: BackgroundKind = BackgroundKind.default
    # Solid color; also shown under an image while it loads.
    color: Color | None = None
    gradient_from: Color | None = None
    gradient_to: Color | None = None
    gradient_angle: int = Field(default=180, ge=0, le=360)
    # The gallery background, for kind "curated".
    curated_id: uuid.UUID | None = None
    # Whether the uploaded image is mostly dark (picks light text when the text
    # color is automatic). The editor measures it on upload.
    image_dark: bool = True

    @model_validator(mode="after")
    def _complete(self) -> ThemeBackground:
        if self.kind == BackgroundKind.solid and self.color is None:
            raise ValueError("a solid background needs a color")
        if self.kind == BackgroundKind.gradient and (
            self.gradient_from is None or self.gradient_to is None
        ):
            raise ValueError("a gradient background needs two colors")
        if self.kind == BackgroundKind.curated and self.curated_id is None:
            raise ValueError("pick a background from the gallery")
        return self


class AvatarBorderKind(enum.StrEnum):
    none = "none"
    solid = "solid"
    gradient = "gradient"


class AvatarBorder(BaseModel):
    kind: AvatarBorderKind = AvatarBorderKind.none
    width: int = Field(default=4, ge=1, le=12)  # px
    color: Color | None = None
    gradient_from: Color | None = None
    gradient_to: Color | None = None
    gradient_angle: int = Field(default=135, ge=0, le=360)

    @model_validator(mode="after")
    def _complete(self) -> AvatarBorder:
        if self.kind == AvatarBorderKind.solid and self.color is None:
            raise ValueError("a solid avatar border needs a color")
        if self.kind == AvatarBorderKind.gradient and (
            self.gradient_from is None or self.gradient_to is None
        ):
            raise ValueError("a gradient avatar border needs two colors")
        return self


class ContentPanel(BaseModel):
    """A panel behind the page's content (header and links), over the page background."""

    enabled: bool = False
    color: Color = "#ffffff"
    opacity: int = Field(default=85, ge=0, le=100)  # percent; lower lets the background through


class Theme(BaseModel):
    background: ThemeBackground = Field(default_factory=ThemeBackground)
    font: Font = Font.system
    # Title, tagline, section headings and social icons. Null = automatic.
    text_color: Color | None = None
    button_style: ButtonStyle = ButtonStyle.filled
    button_shape: ButtonShape = ButtonShape.rounded
    # Link card fill (or border, for outline buttons) and label. Null = automatic.
    button_color: Color | None = None
    button_text_color: Color | None = None
    avatar_shape: AvatarShape = AvatarShape.circle
    avatar_border: AvatarBorder = Field(default_factory=AvatarBorder)
    content: ContentPanel = Field(default_factory=ContentPanel)
