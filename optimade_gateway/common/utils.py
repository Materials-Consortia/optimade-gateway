from enum import Enum
from typing import Any

from pydantic import BaseModel


async def clean_python_types(data: Any) -> Any:
    """Turn data in a list into only using standard Python types.

    Use `dict()` method for Pydantic models.
    Use `value` property for Enums.
    """
    if isinstance(data, (list, tuple, set)):
        res = []
        for datum in data:
            res.append(await clean_python_types(datum))
    elif isinstance(data, dict):
        res = {}
        for key in list(data.keys()):
            res[key] = await clean_python_types(data[key])
    elif isinstance(data, BaseModel):
        # Pydantic model
        res = await clean_python_types(data.dict())
    elif isinstance(data, Enum):
        res = await clean_python_types(data.value)
    else:
        # Unknown or basic type, e.g., str, int, etc.
        res = data
    return res
