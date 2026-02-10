import pytest
from django.utils import timezone
from datetime import timedelta
from ..models import Task
from ..filters import TaskFilterSet

pytestmark = pytest.mark.django_db


class TestTaskFilters:
    """Tests the task filtering feature"""

    def test_filter_by_status(self, user):
        """Test filtering by status"""
        pending = Task.objects.create(
            user=user,
            title='Pending',
            status=Task.TaskStatus.PENDING
        )
        completed = Task.objects.create(
            user=user,
            title='Completed',
            status=Task.TaskStatus.COMPLETED
        )

        queryset = Task.objects.all()
        filterset = TaskFilterSet(
            data={'status': Task.TaskStatus.PENDING},
            queryset=queryset
        )

        filtered = filterset.qs
        assert pending in filtered
        assert completed not in filtered

    def test_filter_by_priority(self, user):
        """Test filtering by priority"""
        high = Task.objects.create(
            user=user,
            title='High',
            priority=Task.TaskPriority.HIGH
        )
        low = Task.objects.create(
            user=user,
            title='Low',
            priority=Task.TaskPriority.LOW
        )

        queryset = Task.objects.all()
        filterset = TaskFilterSet(
            data={'priority': Task.TaskPriority.HIGH},
            queryset=queryset
        )

        assert high in filterset.qs
        assert low not in filterset.qs

    def test_filter_is_overdue(self, user):
        """Test filtering overdue tasks"""
        overdue = Task.objects.create(
            user=user,
            title='Overdue',
            due_date=timezone.now() - timedelta(days=1),
            status=Task.TaskStatus.PENDING
        )
        future = Task.objects.create(
            user=user,
            title='Future',
            due_date=timezone.now() + timedelta(days=7)
        )

        queryset = Task.objects.all()
        filterset = TaskFilterSet(
            data={'is_overdue': True},
            queryset=queryset
        )

        assert overdue in filterset.qs
        assert future not in filterset.qs

    def test_search_in_title(self, user):
        """Test searching in title"""
        task1 = Task.objects.create(user=user, title='Buy groceries')
        task2 = Task.objects.create(user=user, title='Pay bills')

        queryset = Task.objects.all()
        filterset = TaskFilterSet(
            data={'search': 'buy'},
            queryset=queryset
        )

        assert task1 in filterset.qs
        assert task2 not in filterset.qs