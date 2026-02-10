import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from ..serializers import (
    TaskCreateUpdateSerializer,
    TaskDetailSerializer,
    TaskCommentSerializer
)
from ..models import Task

pytestmark = pytest.mark.django_db


class TestTaskCreateUpdateSerializer:
    """Tests the task creation/update serializer"""

    @pytest.fixture
    def factory(self):
        """Create request factory"""
        return APIRequestFactory()

    def test_valid_task_creation(self, user, factory):
        """Test serializer with valid data"""
        request = factory.post('/')
        request.user = user

        data = {
            'title': 'Valid Task',
            'description': 'A valid task description',
            'priority': 'high',
            'due_date': (timezone.now() + timedelta(days=7)).isoformat()
        }

        serializer = TaskCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )

        assert serializer.is_valid()
        task = serializer.save()
        assert task.user == user
        assert task.title == 'Valid Task'

    def test_title_too_short(self, user, factory):
        """Test title validation"""
        request = factory.post('/')
        request.user = user

        data = {
            'title': 'ab'  # Less than 3 characters
        }

        serializer = TaskCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert 'title' in serializer.errors

    def test_due_date_in_past_rejected(self, user, factory):
        """Test past due date rejected"""
        request = factory.post('/')
        request.user = user

        data = {
            'title': 'Valid Title',
            'due_date': (timezone.now() - timedelta(days=1)).isoformat()
        }

        serializer = TaskCreateUpdateSerializer(
            data=data,
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert 'due_date' in serializer.errors