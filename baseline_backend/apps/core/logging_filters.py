"""Logging filter that stamps the active tenant onto every log record, so
production logs can be filtered/correlated per-organization without manually
passing tenant_id into every log call."""
import logging

from apps.core.context import get_current_tenant_id_or_none


class TenantContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        tenant_id = get_current_tenant_id_or_none()
        record.tenant_id = str(tenant_id) if tenant_id else "-"
        return True
