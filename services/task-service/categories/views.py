from django.db.models import Count
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for task categories.
    List endpoint annotates each category with its task count.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Category.objects.annotate(task_count=Count("tasks")).order_by("name")
