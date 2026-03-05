from django.db import models
from categories.models import Category


class Task(models.Model):
    """
    Core task model. owner_id references a user in the User Service —
    we store only the UUID string, no FK to a local user table.
    """

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        IN_REVIEW = "in_review", "In Review"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    # Ownership — stored as a UUID string (no local User model)
    owner_id = models.CharField(max_length=36, db_index=True)

    # Optionally assigned to another user
    assignee_id = models.CharField(max_length=36, blank=True, default="", db_index=True)

    # Core fields
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO, db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True
    )

    # Categorisation
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    tags = models.JSONField(default=list, blank=True)

    # Scheduling
    due_date = models.DateTimeField(null=True, blank=True, db_index=True)
    reminder_sent = models.BooleanField(default=False)

    # Completion tracking
    completed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_id", "status"]),
            models.Index(fields=["owner_id", "due_date"]),
            models.Index(fields=["owner_id", "priority"]),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.title} (owner={self.owner_id})"

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        return (
            self.due_date is not None
            and self.due_date < timezone.now()
            and self.status not in (self.Status.DONE, self.Status.CANCELLED)
        )
