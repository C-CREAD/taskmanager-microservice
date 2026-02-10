import pytest
from rest_framework import status
from ..models import Task

pytestmark = pytest.mark.django_db


class TestTaskViewSet:
    """Tests the Task API endpoints"""

    def test_list_tasks_authenticated(self, authenticated_user, api_client):
        """Test listing tasks requires authentication"""
        user, client = authenticated_user

        response = client.get('/api/tasks/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_tasks_unauthenticated(self, api_client):
        """Test unauthenticated user cannot list tasks"""
        response = api_client.get('/api/tasks/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_task(self, authenticated_user):
        """Test creating a task"""
        user, client = authenticated_user

        data = {
            'title': 'New Task',
            'priority': 'high',
            'due_date': '2024-12-31T23:59:59Z'
        }

        response = client.post('/api/tasks/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Task.objects.filter(title='New Task').exists()

    def test_update_own_task(self, authenticated_user, task):
        """Test user can update their own task"""
        user, client = authenticated_user
        task.user = user
        task.save()

        data = {'title': 'Updated Title'}
        response = client.patch(f'/api/tasks/{task.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.title == 'Updated Title'

    def test_cannot_update_others_task(self, authenticated_user, user, task):
        """Test user cannot update others' tasks"""
        other_user, client = authenticated_user
        task.user = user  # Different user
        task.save()

        data = {'title': 'Hacked'}
        response = client.patch(f'/api/tasks/{task.id}/', data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_own_task(self, authenticated_user, task):
        """Test user can delete their own task"""
        user, client = authenticated_user
        task.user = user
        task.save()

        response = client.delete(f'/api/tasks/{task.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT