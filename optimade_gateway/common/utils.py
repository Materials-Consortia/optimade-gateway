"""Common utility functions.

These functions may be used in general throughout the OPTIMADE Gateway Python code.
"""
from __future__ import annotations

from enum import Enum
from os import getenv
from typing import TYPE_CHECKING

from pydantic import AnyUrl, BaseModel

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    from typing import Any


async def clean_python_types(data: Any, **dump_kwargs: Any) -> Any:
    """Turn any types into MongoDB-friendly Python types.

    Use `model_dump()` method for Pydantic models.
    Use `value` property for Enums.
    Turn tuples and sets into lists.
    """
    if isinstance(data, (list, tuple, set)):
        res = []
        for datum in data:
            res.append(await clean_python_types(datum, **dump_kwargs))
        return res

    if isinstance(data, dict):
        res = {}
        for key in list(data.keys()):
            res[key] = await clean_python_types(data[key], **dump_kwargs)
        return res

    if isinstance(data, BaseModel):
        # Pydantic model
        return await clean_python_types(data.model_dump(**dump_kwargs))

    if isinstance(data, Enum):
        return await clean_python_types(data.value, **dump_kwargs)

    if isinstance(data, type):
        return await clean_python_types(
            f"{data.__module__}.{data.__name__}", **dump_kwargs
        )

    if isinstance(data, AnyUrl):
        return await clean_python_types(str(data), **dump_kwargs)

    # Unknown or other basic type, e.g., str, int, etc.
    return data


def get_resource_attribute(
    resource: BaseModel | dict[str, Any] | None,
    field: str,
    default: Any = None,
    disambiguate: bool = True,
) -> Any:
    """Return a resource's field's value

    Get the field value no matter if the resource is a pydantic model or a Python
    dictionary.

    Determine ambiguous field values and return them if desired (`disambiguate`).
    For example, if
    [`"attributes.base_url"`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResourceAttributes.base_url)
    is requested for a
    [`LinksResource`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResource)
    it can be either a string, a
    [`Link`](https://www.optimade.org/optimade-python-tools/api_reference/models/jsonapi/#optimade.models.jsonapi.Link)
    model or a dictionary resembling the `Link` model.

    Parameters:
        resource: The resource, from which to get the field value.
        field: The resource field. This can be a dot-separated nested field, e.g.,
            `"attributes.base_url"`.
        default: The default value to return if `field` does not exist.
        disambiguate: Whether or not to "shortcut" a field value.
            For example, for `attributes.base_url`, if `True`, this would return the
            string value or the value of it's `"href"` key.

    Returns:
        The resource's field's value.

    """
    if isinstance(resource, BaseModel):
        _get_attr = getattr
    elif isinstance(resource, dict):

        def _get_attr(mapping: dict, key: str, default: Any) -> Any:  # type: ignore[misc]
            return mapping.get(key, default)

    elif resource is None:
        # Allow passing `None`, but simply return `default`
        return default
    else:
        raise TypeError(
            "resource must be either a pydantic model or a Python dictionary, it was "
            f"of type {type(resource)!r}"
        )

    fields = field.split(".")
    for _ in fields[:-1]:
        resource = _get_attr(resource, _, {})
    field = fields[-1]
    value = _get_attr(resource, field, default)

    if (
        disambiguate
        and field in ("base_url", "next", "prev", "last", "first")
        and not isinstance(value, (str, AnyUrl))
    ):
        value = _get_attr(value, "href", default)

    return value
