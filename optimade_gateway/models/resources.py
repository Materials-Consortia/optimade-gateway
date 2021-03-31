from datetime import datetime
from typing import Any, Optional

from optimade.models import EntryResourceAttributes


class EntryResourceCreate(EntryResourceAttributes):
    """Generic model for creating new entry resources in the MongoDB"""

    last_modified: Optional[datetime]

    id: Optional[str]

    class Config:
        extra = "ignore"

    @classmethod
    def _remove_pre_root_validators(cls):
        """Remove `check_illegal_attributes_fields` pre root_validators"""
        pre_root_validators = []
        for validator in cls.__pre_root_validators__:
            if not str(validator).startswith(
                "<function Attributes.check_illegal_attributes_fields"
            ):
                pre_root_validators.append(validator)
        cls.__pre_root_validators__ = pre_root_validators

    def __init__(self, **data: Any) -> None:
        """Remove root_validator `check_illegal_attributes_fields`"""
        self._remove_pre_root_validators()
        super().__init__(**data)
