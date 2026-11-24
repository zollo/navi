"""Curated background schemas."""
from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, StringConstraints

MAX_NAME = 80
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME)
]


class BackgroundRead(BaseModel):
    id: uuid.UUID
    name: str
    # Relative URL of the image; it never changes, so it can be cached for good.
    image_url: str
    # Mostly dark image: pages using it default to light text.
    dark: bool


class BackgroundList(BaseModel):
    backgrounds: list[BackgroundRead]


class BackgroundUpdate(BaseModel):
    name: Name | None = None
    dark: bool | None = None
