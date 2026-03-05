from django.http import JsonResponse
from django.db import connection


def health_view(request):
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "service": "TaskForge Task Service",
            "version": "1.0.0",
            "database": "connected" if db_ok else "unreachable",
        },
        status=200 if db_ok else 503,
    )
