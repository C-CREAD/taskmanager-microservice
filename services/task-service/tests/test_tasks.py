"""
Tests for the Task Service.
Run with: python manage.py test tests
or: pytest tests/ --ds=taskservice.settings -v

Authentication is mocked so no User Service is needed.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from categories.models import Category
from tasks.models import Task


def make_user(user_id="user-001", username="testuser", email="test@example.com"):
    """Create a mock RemoteUser for injection into requests."""
    from taskservice.authentication import RemoteUser
    return RemoteUser(id=user_id, email=email, username=username)


class AuthenticatedTestCase(TestCase):
    """Base class that patches authentication for all test methods."""

    def setUp(self):
        self.user_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self.user = make_user(user_id=self.user_id)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(
            name="Work", color="#3b82f6", icon="💼"
        )

    def _make_task(self, **kwargs):
        defaults = dict(
            owner_id=self.user_id,
            title="Sample Task",
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
        )
        defaults.update(kwargs)
        return Task.objects.create(**defaults)


class TaskCRUDTests(AuthenticatedTestCase):

    def test_create_task(self):
        resp = self.client.post(
            "/api/tasks/",
            {
                "title": "Write unit tests",
                "description": "Cover all edge cases",
                "priority": "high",
                "category": self.category.id,
                "tags": ["testing", "python"],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["title"], "Write unit tests")
        self.assertEqual(data["owner_id"], self.user_id)
        self.assertEqual(data["priority"], "high")
        self.assertIn("testing", data["tags"])

    def test_list_tasks_scoped_to_owner(self):
        self._make_task(title="My Task")
        Task.objects.create(owner_id="other-user-999", title="Other's Task")

        resp = self.client.get("/api/tasks/")
        self.assertEqual(resp.status_code, 200)
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("My Task", titles)
        self.assertNotIn("Other's Task", titles)

    def test_retrieve_task(self):
        task = self._make_task(title="Retrieve Me")
        resp = self.client.get(f"/api/tasks/{task.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Retrieve Me")

    def test_update_task(self):
        task = self._make_task()
        resp = self.client.patch(
            f"/api/tasks/{task.id}/",
            {"title": "Updated Title", "priority": "urgent"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "Updated Title")

    def test_delete_task(self):
        task = self._make_task()
        resp = self.client.delete(f"/api/tasks/{task.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_cannot_access_other_users_task(self):
        other_task = Task.objects.create(
            owner_id="stranger-999", title="Private Task"
        )
        resp = self.client.get(f"/api/tasks/{other_task.id}/")
        self.assertEqual(resp.status_code, 404)


class TaskFilterTests(AuthenticatedTestCase):

    def test_filter_by_status(self):
        self._make_task(title="Todo", status=Task.Status.TODO)
        self._make_task(title="Done", status=Task.Status.DONE)

        resp = self.client.get("/api/tasks/?status=todo")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Todo", titles)
        self.assertNotIn("Done", titles)

    def test_filter_by_priority(self):
        self._make_task(title="Urgent", priority=Task.Priority.URGENT)
        self._make_task(title="Low", priority=Task.Priority.LOW)

        resp = self.client.get("/api/tasks/?priority=urgent")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Urgent", titles)
        self.assertNotIn("Low", titles)

    def test_filter_overdue(self):
        past = timezone.now() - timezone.timedelta(days=1)
        future = timezone.now() + timezone.timedelta(days=1)
        self._make_task(title="Overdue", due_date=past)
        self._make_task(title="Future", due_date=future)

        resp = self.client.get("/api/tasks/?overdue=true")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Overdue", titles)
        self.assertNotIn("Future", titles)

    def test_search_by_title(self):
        self._make_task(title="Fix login bug")
        self._make_task(title="Update readme")

        resp = self.client.get("/api/tasks/?search=login")
        titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Fix login bug", titles)
        self.assertNotIn("Update readme", titles)


class TaskStatusTransitionTests(AuthenticatedTestCase):

    def test_valid_transition_todo_to_in_progress(self):
        task = self._make_task(status=Task.Status.TODO)
        resp = self.client.patch(
            f"/api/tasks/{task.id}/status/",
            {"status": "in_progress"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "in_progress")

    def test_invalid_transition_todo_to_done(self):
        task = self._make_task(status=Task.Status.TODO)
        resp = self.client.patch(
            f"/api/tasks/{task.id}/status/",
            {"status": "done"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_complete_action(self):
        task = self._make_task(status=Task.Status.IN_PROGRESS)
        with patch("tasks.views.notify_task_completed"):
            resp = self.client.post(f"/api/tasks/{task.id}/complete/")
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)
        self.assertIsNotNone(task.completed_at)


class TaskStatsTests(AuthenticatedTestCase):

    def test_stats_endpoint(self):
        self._make_task(status=Task.Status.TODO)
        self._make_task(status=Task.Status.DONE)
        self._make_task(status=Task.Status.IN_PROGRESS)

        resp = self.client.get("/api/tasks/stats/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["by_status"]["todo"], 1)
        self.assertEqual(data["by_status"]["done"], 1)
