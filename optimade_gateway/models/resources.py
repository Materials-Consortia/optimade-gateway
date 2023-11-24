"""Pydantic models/schemas for entry-endpoint resources.

This module is mainly used for a special pydantic base model, which can be used as a
mix-in class when creating entry-endpoint resources.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from optimade.models import EntryResourceAttributes
from pydantic import ConfigDict


class EntryResourceCreate(EntryResourceAttributes):
    """Generic model for creating new entry resources in the MongoDB"""

    model_config = ConfigDict(extra="ignore")

    last_modified: datetime | None

    id: str | None

    @classmethod
    def _remove_pre_root_validators(cls):
        """Remove `check_illegal_attributes_fields` pre root_validators."""
        pre_root_validators = []
        for validator in cls.__pre_root_validators__:
            if not str(validator).startswith(
                "<function Attributes.check_illegal_attributes_fields"
            ):
                pre_root_validators.append(validator)
        cls.__pre_root_validators__ = pre_root_validators

    def __init__(self, **data: Any) -> None:
        """Remove root_validator `check_illegal_attributes_fields`."""
        self._remove_pre_root_validators()
        super().__init__(**data)
