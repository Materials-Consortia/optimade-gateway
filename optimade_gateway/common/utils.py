"""Common utility functions.

These functions may be used in general throughout the OPTIMADE Gateway Python code.
"""
# pylint: disable=line-too-long
from enum import Enum
import json
from os import getenv
from typing import TYPE_CHECKING

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.responses import HTMLResponse

from optimade_gateway.common.config import CONFIG

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    # pylint: disable=unused-import
    from typing import Any, Dict, Optional, Union


async def clean_python_types(data: "Any") -> "Any":
    """Turn any types into MongoDB-friendly Python types.

    Use `dict()` method for Pydantic models.
    Use `value` property for Enums.
    Turn tuples and sets into lists.
    """
    res: "Any" = None
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
    elif isinstance(data, type):
        res = await clean_python_types(f"{data.__module__}.{data.__name__}")
    else:
        # Unknown or other basic type, e.g., str, int, etc.
        res = data
    return res


def get_resource_attribute(
    resource: "Union[BaseModel, Dict[str, Any], None]",
    field: str,
    default: "Any" = None,
    disambiguate: bool = True,
) -> "Any":
    """Return a resource's field's value

    Get the field value no matter if the resource is a pydantic model or a Python dictionary.

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

        def _get_attr(mapping: dict, key: str, default: "Any") -> "Any":  # type: ignore[misc]
            return mapping.get(key, default)

    elif resource is None:
        # Allow passing `None`, but simply return `default`
        return default
    else:
        raise TypeError(
            "resource must be either a pydantic model or a Python dictionary, it was of "
            f"type {type(resource)!r}"
        )

    fields = field.split(".")
    for _ in fields[:-1]:
        resource = _get_attr(resource, _, {})
    field = fields[-1]
    value = _get_attr(resource, field, default)

    if disambiguate:
        if field in ("base_url", "next", "prev", "last", "first"):
            if not isinstance(value, str):
                value = _get_attr(value, "href", default)

    return value


def gateway_get_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css",
    swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    oauth2_redirect_url: "Optional[str]" = None,
    init_oauth: "Optional[Dict[str, Any]]" = None,
) -> HTMLResponse:
    """A copy of `fastapi.openapi.docs.get_swagger_ui_html()`.

    Redone here to ensure a correct `oauth2RedirectUrl`.
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
    <link rel="shortcut icon" href="{swagger_favicon_url}">
    <title>{title}</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{swagger_js_url}"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({{
        url: '{openapi_url}',
    """

    if oauth2_redirect_url:
        html += f"oauth2RedirectUrl: '{CONFIG.base_url}{oauth2_redirect_url}',"

    html += """
        dom_id: '#swagger-ui',
        presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        deepLinking: true,
        showExtensions: true,
        showCommonExtensions: true
    })"""

    if init_oauth:
        html += f"""
        ui.initOAuth({json.dumps(jsonable_encoder(init_oauth))})
        """

    html += """
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
