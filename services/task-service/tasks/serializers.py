from django.utils import timezone
from rest_framework import serializers

from categories.serializers import CategorySerializer
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source="category", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "owner_id",
            "assignee_id",
            "title",
            "description",
            "status",
            "priority",
            "category",
            "category_detail",
            "tags",
            "due_date",
            "reminder_sent",
            "is_overdue",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner_id",
            "reminder_sent",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list of strings.")
        if any(not isinstance(t, str) for t in value):
            raise serializers.ValidationError("Each tag must be a string.")
        if len(value) > 10:
            raise serializers.ValidationError("A task may have at most 10 tags.")
        return [t.strip().lower() for t in value]

    def validate_due_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value


class TaskCreateSerializer(TaskSerializer):
    """Used for POST — owner_id is injected from the authenticated user, not the request body."""

    class Meta(TaskSerializer.Meta):
        read_only_fields = TaskSerializer.Meta.read_only_fields  # owner_id stays read-only


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """Lightweight serializer for PATCH /tasks/{id}/status"""

    class Meta:
        model = Task
        fields = ["status"]

    def validate_status(self, value):
        task = self.instance
        allowed_transitions = {
            Task.Status.TODO:        {Task.Status.IN_PROGRESS, Task.Status.CANCELLED},
            Task.Status.IN_PROGRESS: {Task.Status.IN_REVIEW, Task.Status.TODO, Task.Status.CANCELLED},
            Task.Status.IN_REVIEW:   {Task.Status.DONE, Task.Status.IN_PROGRESS},
            Task.Status.DONE:        set(),  # terminal
            Task.Status.CANCELLED:   set(),  # terminal
        }
        current = task.status
        if value not in allowed_transitions.get(current, set()):
            raise serializers.ValidationError(
                f"Cannot transition from '{current}' to '{value}'. "
                f"Allowed: {allowed_transitions.get(current, set()) or 'none (terminal state)'}."
            )
        return value
