from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    TaskViewSet,
    TaskCommentViewSet,
    TaskLabelViewSet,
    health_check
)

# Main router for tasks and labels:
router = DefaultRouter()
router.register(r'tasks', TaskViewSet, 'task')
router.register(r'labels', TaskLabelViewSet, 'label')

# Nested router for task comments
tasks_router = routers.NestedDefaultRouter(
    router,
    'tasks',
    lookup='task'
)
tasks_router.register(
    'comments',
    TaskCommentViewSet,
    basename='task-comments'
)

# URL patterns to access url viewpoints
urlpatterns = [
    path('', include(router.urls)),
    path('', include(tasks_router.urls)),
    path('health_check/', health_check, name='health-check'),
]