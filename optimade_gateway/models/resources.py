"""Pydantic models/schemas for entry-endpoint resources.

This module is mainly used for a special pydantic base model, which can be used as a
mix-in class when creating entry-endpoint resources.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from optimade.models import EntryResourceAttributes
from pydantic import ConfigDict, model_validator


class EntryResourceCreate(EntryResourceAttributes):
    """Generic model for creating new entry resources in the MongoDB"""

    model_config = ConfigDict(extra="ignore")

    last_modified: Optional[datetime] = None

    id: Optional[str] = None

    @model_validator(mode="after")
    def check_illegal_attributes_fields(self) -> EntryResourceCreate:
        """Overwrite parental `check_illegal_attributes_fields` class validators."""
        return self
