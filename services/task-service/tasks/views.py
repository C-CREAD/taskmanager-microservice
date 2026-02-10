from django.core.exceptions import FieldError
from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsTaskOwner
from .models import Task, TaskComment, TaskLabel, TaskQuerySet
from .serializers import (TaskCreateUpdateSerializer, TaskListSerializer, TaskDetailSerializer,
                          TaskCommentSerializer, TaskLabelSerializer, BulkTaskUpdateSerializer,
                          TaskStatisticsSerializer)
from .filters import TaskFilterSet
from .tasks import send_due_date_reminder, bulk_update_tasks


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for performing CRUD operations
    """
    permission_classes = [IsAuthenticated, IsTaskOwner]
    filterset_class = TaskFilterSet
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get user's tasks"""
        return Task.objects.filter(
            user=self.request.user,
            is_deleted = False
        )

    def get_serializer_class(self):
        """Get serializer based on action"""
        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return TaskCreateUpdateSerializer
        elif self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskDetailSerializer

    def create_task(self, serializer):
        """Create task with current user"""
        serializer.save(user=self.request.user)

    def soft_delete_task(self, instance):
        """Soft delete task"""
        instance.soft_delete()

    @action(detail=True, methods=['get', 'post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        """
        Mark task as completed.

        POST /api/tasks/{id}/mark-completed/
        """
        task = self.get_object()

        if request.method == 'POST':
            task.mark_completed()
            # Queue async reminder if needed
            send_due_date_reminder.delay(task.id)

        return Response(
            TaskDetailSerializer(task).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get', 'post'], url_path='mark-in-progress')
    def mark_in_progress(self, request, pk=None):
        """Mark task as in progress"""
        task = self.get_object()

        if request.method == 'POST':
            task.mark_in_progress()

        return Response(
            TaskDetailSerializer(task).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get', 'post'], url_path='mark-cancelled')
    def mark_cancelled(self, request, pk=None):
        """Mark task as cancelled"""
        task = self.get_object()

        if request.method == 'POST':
            task.mark_cancelled()

        return Response(
            TaskDetailSerializer(task).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update multiple tasks.

        POST /api/tasks/bulk-update/
        {
            "task_ids": ["id1", "id2", "id3"],
            "status": "completed",
            "priority": "high"
        }
        """
        serializer = BulkTaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_ids = serializer.validated_data['task_ids']
        updates = {
            k: v for k, v in serializer.validated_data.items()
            if k != 'task_ids' and v is not None
        }

        # Queue async bulk update
        bulk_update_tasks.delay(
            user_id=str(request.user.id),
            task_ids=[str(id) for id in task_ids],
            updates=updates
        )

        return Response(
            {
                'status': 'processing',
                'message': f'Updating {len(task_ids)} tasks'
            },
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=False, methods=['get'])
    def get_statistics(self):
        """
        Get task statistics.

        GET /api/tasks/statistics/
        """
        tasks = self.get_queryset()

        total = tasks.count()
        completed = tasks.filter(status=Task.TaskStatus.COMPLETED).count()
        pending = tasks.filter(status=Task.TaskStatus.PENDING).count()
        in_progress = tasks.filter(status=Task.TaskStatus.IN_PROGRESS).count()
        overdue = tasks.overdue().count()

        completion_rate = (completed / total * 100) if total > 0 else 0

        # Calculate average completion time
        completed_tasks = tasks.filter(
            status=Task.TaskStatus.COMPLETED,
            completed_at__isnull=False
        )
        avg_time = 0
        if completed_tasks.exists():
            total_days = sum([
                (t.completed_at - t.created_at).days
                for t in completed_tasks
            ])
            avg_time = total_days / completed_tasks.count()

        # Group by priority
        tasks_by_priority = {}
        for priority in Task.TaskPriority.choices:
            count = tasks.filter(priority=priority[0]).count()
            if count > 0:
                tasks_by_priority[priority[1]] = count

        # Group by category
        tasks_by_category = {}
        for category in tasks.values_list('category', flat=True).distinct():
            if category:
                count = tasks.filter(category=category).count()
                tasks_by_category[category] = count

        stats = {
            'total_tasks': total,
            'completed_tasks': completed,
            'pending_tasks': pending,
            'in_progress_tasks': in_progress,
            'overdue_tasks': overdue,
            'completion_rate': round(completion_rate, 2),
            'average_completion_time': round(avg_time, 1),
            'tasks_by_priority': tasks_by_priority,
            'tasks_by_category': tasks_by_category,
        }

        serializer = TaskStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self):
        """Get overdue tasks"""
        tasks = self.get_queryset().overdue()

        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def due_soon(self):
        """Get tasks due within 24 hours"""
        tasks = self.get_queryset().filter(
            due_date__range=[
                timezone.now(),
                timezone.now() + timezone.timedelta(hours=24)
            ],
            status__in=['pending', 'in_progress']
        )

        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = TaskListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskCommentSerializer

    def get_queryset(self):
        """Get comments for specific comment"""
        task_pk = self.kwargs.get('task_pk')
        return TaskComment.objects.filter(
            task_id=task_pk,
            is_deleted=False
        ).select_related('author')

    def create_comment(self, serializer):
        """Create comment"""
        task_pk = self.kwargs.get('task_pk')
        serializer.save(
            author=self.request.user,
            task_id=task_pk
        )

    def soft_delete_comment(self, instance):
        """Soft delete comment"""
        instance.is_deleted = True
        instance.save()


class TaskLabelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskLabelSerializer

    def get_queryset(self):
        """Get comments for specific task"""
        return TaskLabel.objects.filter(user=self.request.user)

    def create_label(self, serializer):
        """Create comment"""
        serializer.save(author=self.request.user)


def health_check(request):
    """Health check endpoint"""
    from django.http import JsonResponse
    return JsonResponse({
        'status': 'healthy ✅',
        'service': 'task-service',
        'timestamp': timezone.now().isoformat()
    })