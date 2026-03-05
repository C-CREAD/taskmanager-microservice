from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "status", "priority", "category", "owner_id",
                    "assignee_id", "due_date", "reminder_sent", "created_at", ]
    list_filter  = ["status", "priority", "category", "reminder_sent", ]
    search_fields = ["title", "description", "owner_id", "assignee_id", ]
    ordering     = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "completed_at", "reminder_sent", ]

    fieldsets = (
        ("Core", {
            "fields": ("title", "description", "status", "priority", "category", "tags")
        }),
        ("Ownership", {
            "fields": ("owner_id", "assignee_id")
        }),
        ("Scheduling", {
            "fields": ("due_date", "reminder_sent", "completed_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
