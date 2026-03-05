from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "color", "icon", "task_count", "created_at"]
        read_only_fields = ["id", "created_at", "task_count"]
