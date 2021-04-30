from fastapi import Request
from fastapi.exceptions import RequestValidationError
from optimade.models import ErrorSource, OptimadeError
from optimade.server.exception_handlers import general_exception
from starlette.responses import JSONResponse


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Special handler if a `RequestValidationError` comes from wrong `POST` data"""
    status_code = 500
    if request.method in ("POST", "post"):
        status_code = 400

    errors = set()
    for error in exc.errors():
        pointer = "/" + "/".join([str(_) for _ in error["loc"]])
        source = ErrorSource(pointer=pointer)
        code = error["type"]
        detail = error["msg"]
        errors.add(
            OptimadeError(
                detail=detail,
                status=status_code,
                title=str(exc.__class__.__name__),
                source=source,
                code=code,
            )
        )

    return general_exception(request, exc, status_code=status_code, errors=list(errors))
