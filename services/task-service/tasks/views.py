from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import TaskFilter
from .models import Task
from .permissions import IsTaskOwner
from .serializers import TaskCreateSerializer, TaskSerializer, TaskStatusUpdateSerializer
from .services import (
    mark_task_complete,
    notify_task_assigned,
    notify_task_completed,
    notify_task_created,
)


class TaskViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for tasks, scoped to the authenticated user.

    List endpoints support filtering via TaskFilter and search/ordering
    via DRF's built-in backends.

    Extra actions:
      PATCH /tasks/{id}/status  — validated status transition
      POST  /tasks/{id}/complete — shortcut to mark done
      GET   /tasks/stats         — quick summary counts for the current user
    """

    permission_classes = [IsAuthenticated, IsTaskOwner]
    filterset_class = TaskFilter
    search_fields = ["title", "description", "tags"]
    ordering_fields = ["created_at", "updated_at", "due_date", "priority", "status"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """
        Scope all queries to tasks owned by OR assigned to the current user.
        """
        user_id = str(self.request.user.id)
        return (
            Task.objects.filter(owner_id=user_id)
            | Task.objects.filter(assignee_id=user_id)
        ).select_related("category").distinct()

    def get_serializer_class(self):
        if self.action == "create":
            return TaskCreateSerializer
        if self.action == "update_status":
            return TaskStatusUpdateSerializer
        return TaskSerializer

    def get_permissions(self):
        # List and create don't need object-level checks
        if self.action in ("list", "create", "stats"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsTaskOwner()]

    def perform_create(self, serializer):
        task = serializer.save(owner_id=str(self.request.user.id))
        # Notify owner (fire-and-forget)
        auth_token = self.request.auth
        notify_task_created(task, auth_token)
        if task.assignee_id:
            notify_task_assigned(task, auth_token)

    def perform_update(self, serializer):
        old_assignee = self.get_object().assignee_id
        task = serializer.save()
        # Notify new assignee if changed
        if task.assignee_id and task.assignee_id != old_assignee:
            notify_task_assigned(task, self.request.auth)

    # ── Custom actions ────────────────────────────────────────────────────────────

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """
        PATCH /api/v1/tasks/{id}/status
        Validates the transition through TaskStatusUpdateSerializer.
        """
        task = self.get_object()
        serializer = TaskStatusUpdateSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]

        if new_status == Task.Status.DONE:
            task = mark_task_complete(task)
            notify_task_completed(task, request.auth)
        else:
            serializer.save()
            task.refresh_from_db()

        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """
        POST /api/v1/tasks/{id}/complete
        Shortcut to mark a task as DONE without going through status transitions.
        """
        task = self.get_object()
        if task.status in (Task.Status.DONE, Task.Status.CANCELLED):
            return Response(
                {"detail": f"Task is already '{task.status}' and cannot be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task = mark_task_complete(task)
        notify_task_completed(task, request.auth)
        return Response(TaskSerializer(task).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        GET /api/v1/tasks/stats
        Returns a quick summary of the authenticated user's task counts.
        """
        user_id = str(request.user.id)
        qs = Task.objects.filter(owner_id=user_id)

        now = timezone.now()
        data = {
            "total": qs.count(),
            "by_status": {
                s.value: qs.filter(status=s).count() for s in Task.Status
            },
            "by_priority": {
                p.value: qs.filter(priority=p).count() for p in Task.Priority
            },
            "overdue": qs.filter(
                due_date__lt=now
            ).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED]).count(),
            "due_today": qs.filter(
                due_date__date=now.date()
            ).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED]).count(),
            "completed_today": qs.filter(completed_at__date=now.date()).count(),
        }
        return Response(data)
