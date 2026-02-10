from django.test import TestCase
import pytest
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from ..models import Task, TaskActivity

pytestmark = pytest.mark.django_db


class TestTaskModel:
    """Testing the Task model"""

    def test_create_task(self, user):
        """Test creating a task"""
        task = Task.objects.create(
            user=user,
            title="Test Task",
            description="Test Description"
        )

        assert task.id is not None
        assert task.user == user
        assert task.title == "Test Task"
        assert task.status == Task.TaskStatus.PENDING

    def test_task_str_representation(self, task):
        """Test task string representation"""
        assert str(task) == f"{task.title} | {task.priority} | {task.status}"

    def test_is_overdue_property(self, user):
        """Test is_overdue property"""
        # Non-overdue task
        future_task = Task.objects.create(
            user=user,
            title="Future",
            due_date=timezone.now() + timedelta(days=1)
        )
        assert not future_task.is_overdue

        # Overdue task
        past_task = Task.objects.create(
            user=user,
            title="Past",
            due_date=timezone.now() - timedelta(days=1),
            status=Task.TaskStatus.PENDING
        )
        assert past_task.is_overdue

    def test_mark_completed(self, task):
        """Test marking task as completed"""
        task.mark_completed()

        assert task.status == Task.TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.completion_percentage == 100

    def test_days_remaining(self, user):
        """Test days_remaining calculation"""
        due_date = timezone.now() + timedelta(days=5)
        task = Task.objects.create(
            user=user,
            title="Task",
            due_date=due_date
        )

        assert task.days_until_due == 5

    def test_task_with_null_due_date(self, user):
        """Test task without due date"""
        task = Task.objects.create(
            user=user,
            title="No Due Date",
            due_date=None
        )

        assert task.due_date is None
        assert task.days_until_due is None

    def test_task_ordering(self, user):
        """Test tasks are ordered by creation date"""
        t1 = Task.objects.create(user=user, title="First")
        t2 = Task.objects.create(user=user, title="Second")

        tasks = list(Task.objects.all())
        assert tasks[0] == t2  # Most recent first
        assert tasks[1] == t1


class TestTaskActivityModel:
    """Test TaskActivity (audit log)"""

    def test_create_activity(self, task, user):
        """Test creating activity log"""
        activity = TaskActivity.objects.create(
            task=task,
            field_name='status',
            old_value='pending',
            new_value='in_progress',
            changed_by=user
        )

        assert activity.task == task
        assert activity.field_name == 'status'
        assert activity.old_value == 'pending'
        assert activity.new_value == 'in_progress'

    def test_activity_ordering(self, task, user):
        """Test activities ordered by change date"""
        a1 = TaskActivity.objects.create(
            task=task,
            field_name='status',
            old_value='pending',
            new_value='in_progress',
            changed_by=user
        )
        a2 = TaskActivity.objects.create(
            task=task,
            field_name='status',
            old_value='in_progress',
            new_value='completed',
            changed_by=user
        )

        activities = list(TaskActivity.objects.all())
        assert activities[0] == a2  # Most recent first