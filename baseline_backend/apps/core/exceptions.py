"""Custom DRF exception handler.

Ensures every API error response has a consistent shape (`{"detail": ...,
"code": ...}`) and that unhandled exceptions never leak a stack trace or
internal exception message to the client — they're logged server-side with
full detail and returned to the client as a generic 500.
"""
import logging
import uuid

from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.context import TenantContextError

logger = logging.getLogger(__name__)


def baseline_exception_handler(exc, context):
    if isinstance(exc, TenantContextError):
        # This should never surface to a client — it means a code path ran
        # tenant-scoped ORM access outside the middleware/context-manager
        # boundary. Treat it as a bug, not a client error.
        logger.error("TenantContextError reached the exception handler: %s", exc)
        return Response({"detail": "Internal server error.", "code": "internal_error"}, status=500)

    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
        response.data = {"detail": detail, "code": getattr(exc, "default_code", "error")}
        return response

    # Unhandled exception: log with a correlation id, return a generic body.
    error_id = uuid.uuid4()
    logger.exception("Unhandled exception [error_id=%s]", error_id)
    return Response(
        {"detail": "An unexpected error occurred.", "code": "internal_error", "error_id": str(error_id)},
        status=500,
    )
