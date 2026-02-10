import pytest
from unittest.mock import patch, MagicMock
from celery.result import AsyncResult
from ..tasks import (
    send_due_date_reminder,
    send_overdue_notification,
    bulk_update_tasks,
)

from ..models import Task

pytestmark = pytest.mark.django_db


class TestCeleryTasks:
    """Tests the Celery asynchronous tasks"""

    @patch('tasks.tasks.requests.post')
    def test_send_reminder_success(self, mock_post, task):
        """Test successful reminder sending"""
        mock_post.return_value = MagicMock(status_code=200)

        result = send_due_date_reminder(task.id)

        # Task should be marked as sent
        task.refresh_from_db()
        assert task.reminder_sent
        mock_post.assert_called_once()

    @patch('tasks.tasks.requests.post')
    def test_send_reminder_already_sent(self, mock_post, task):
        """Test reminder not sent twice"""
        task.reminder_sent = True
        task.save()

        result = send_due_date_reminder(task.id)

        # Should not call notification service
        mock_post.assert_not_called()

    def test_bulk_update_tasks(self, user):
        """Test bulk updating tasks"""
        task1 = Task.objects.create(
            user=user,
            title='Task 1',
            status=Task.TaskStatus.PENDING
        )
        task2 = Task.objects.create(
            user=user,
            title='Task 2',
            status=Task.TaskStatus.PENDING
        )

        result = bulk_update_tasks(
            user_id=user.id,
            task_ids=[str(task1.id), str(task2.id)],
            updates={'status': Task.TaskStatus.COMPLETED}
        )

        task1.refresh_from_db()
        task2.refresh_from_db()
        assert task1.status == Task.TaskStatus.COMPLETED
        assert task2.status == Task.TaskStatus.COMPLETED
        assert result['updated_count'] == 2