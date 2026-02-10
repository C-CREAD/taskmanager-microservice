import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from factory.django import DjangoModelFactory
from factory import Faker, SubFactory, LazyFunction
from ..models import Task, TaskLabel, TaskComment, TaskStatus, TaskPriority
from django.utils import timezone


class UserFactory(DjangoModelFactory):
    """Factory for creating test users"""

    class Meta:
        model = User

    username = Faker('user_name')
    email = Faker('email')
    first_name = Faker('first_name')
    last_name = Faker('last_name')
    is_active = True

    @classmethod
    def create_batch(cls, size, **kwargs):
        """Create multiple users"""
        return super().create_batch(size, **kwargs)


class TaskFactory(DjangoModelFactory):
    """Factory for creating test tasks"""

    class Meta:
        model = Task

    user = SubFactory(UserFactory)
    title = Faker('sentence', nb_words=4)
    description = Faker('text', max_nb_chars=200)
    status = TaskStatus.PENDING
    priority = TaskPriority.MEDIUM
    category = Faker('word')
    due_date = LazyFunction(
        lambda: timezone.now() + timezone.timedelta(days=7)
    )


class TaskLabelFactory(DjangoModelFactory):
    """Factory for creating test labels"""

    class Meta:
        model = TaskLabel

    user = SubFactory(UserFactory)
    name = Faker('word')
    color = '#808080'


class TaskCommentFactory(DjangoModelFactory):
    """Factory for creating test comments"""

    class Meta:
        model = TaskComment

    task = SubFactory(TaskFactory)
    author = SubFactory(UserFactory)
    content = Faker('text', max_nb_chars=500)


@pytest.fixture
def user():
    """Create a single test user"""
    return UserFactory()


@pytest.fixture
def authenticated_user(user):
    """Create user and return with client"""
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.fixture
def task(user):
    """Create a task for a user"""
    return TaskFactory(user=user)


@pytest.fixture
def task_with_labels(user):
    """Create a task with labels"""
    task = TaskFactory(user=user)
    labels = TaskLabelFactory.create_batch(3, user=user)
    task.labels.set(labels)
    return task


@pytest.fixture
def multiple_tasks(user):
    """Create multiple tasks"""
    return TaskFactory.create_batch(5, user=user)


@pytest.fixture
def overdue_task(user):
    """Create an overdue task"""
    return TaskFactory(
        user=user,
        due_date=timezone.now() - timezone.timedelta(days=1),
        status=Task.TaskStatus.PENDING
    )


@pytest.fixture
def completed_task(user):
    """Create a completed task"""
    return TaskFactory(
        user=user,
        status=Task.TaskStatus.COMPLETED,
        completed_at=timezone.now(),
        completion_percentage=100
    )


@pytest.fixture
def api_client():
    """Create unauthenticated API client"""
    return APIClient()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests"""
    pass


@pytest.fixture
def celery_config():
    """Configure Celery for testing"""
    return {
        'broker_url': 'memory://',
        'result_backend': 'cache+memory://',
        'task_always_eager': True,  # Execute tasks synchronously
    }