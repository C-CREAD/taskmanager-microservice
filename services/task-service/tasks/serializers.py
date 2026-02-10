from rest_framework import serializers
from django.utils import timezone
from .models import Task, TaskComment, TaskLabel, TaskAttachment, TaskActivity, TaskStatus, TaskPriority, TaskQuerySet
# from shared.constants import TASK_STATUSES, TASK_PRIORITIES


class TaskLabelSerializer(serializers.ModelSerializer):
    """Serializer for task labels"""

    class Meta:
        model = TaskLabel
        fields = ['id', 'name', 'color', 'created_at']
        read_only_fields = ['id', 'created_at']


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments with nested author info"""

    author_username = serializers.CharField(
        source='author.username',
        read_only=True
    )
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'content', 'author', 'author_username',
                  'author_avatar', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_author_avatar(self, obj):
        """Get author's avatar URL"""
        # Could call User Service here for avatar
        return None

    def create(self, validated_data):
        """Auto-assign current user as author"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class TaskActivitySerializer(serializers.ModelSerializer):
    """Serializer for activity log entries"""

    changed_by_username = serializers.CharField(
        source='changed_by.username',
        read_only=True
    )

    class Meta:
        model = TaskActivity
        fields = [
            'id', 'field_name', 'old_value', 'new_value',
            'changed_by_username', 'changed_at'
        ]
        read_only_fields = fields


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating tasks. Includes validation rules for
    certain fields like Task title, due date, estimated duration, and labels.
    """

    labels = serializers.PrimaryKeyRelatedField(
        queryset=TaskLabel.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority', 'category', 'labels',
            'due_date', 'estimated_duration', 'completion_percentage'
        ]
        extra_kwargs = {
            'title': {
                'required': True,
                'allow_blank': False
            },
            'description': {
                'required': False,
                'allow_blank': True
            }
        }

    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Title must be at least 3 characters long"
            )
        return value.strip()

    def validate_due_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError(
                "Due date must be in the future"
            )
        return value

    def validate_estimated_duration(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Duration must be greater than 0"
            )
        return value

    def validate_labels(self, value):
        """Ensure labels belong to current user"""
        user = self.context['request'].user
        for label in value:
            if label.user != user:
                raise serializers.ValidationError(
                    f"Label '{label.name}' does not belong to you"
                )
        return value

    def validate(self, data):
        """
        Performs validation across due date and estimated duration fields.
        """
        # If task is marked for tomorrow, it should have reasonable duration
        due_date = data.get('due_date')
        estimated_duration = data.get('estimated_duration')

        if due_date and estimated_duration:
            hours_available = (due_date - timezone.now()).total_seconds() / 3600
            hours_needed = estimated_duration / 60

            if hours_needed > hours_available:
                raise serializers.ValidationError(
                    "Estimated duration exceeds time until due date"
                )
        return data

    def create(self, validated_data):
        """Create task with current user"""
        labels = validated_data.pop('labels', [])
        task = Task.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        task.labels.set(labels)
        return task

    def update(self, instance, validated_data):
        labels = validated_data.pop('labels', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if labels is not None:
            instance.labels.set(labels)

        return instance


class TaskListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing tasks.
    """

    labels = TaskLabelSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'user', 'title', 'status', 'priority', 'due_date', 'created_at',
            'category', 'labels', 'user_email', 'is_overdue', 'days_until_due',
            'completion_percentage', 'comment_count'
        ]
        read_only_fields = fields

    def get_is_overdue(self, obj):
        """Check if task is overdue"""
        return obj.is_overdue

    def get_days_until_due(self, obj):
        """Days until due (or days overdue if negative)"""
        return obj.days_until_due

    def get_comment_count(self, obj):
        """Count comments (cached in view if possible)"""
        return obj.comments.filter(is_deleted=False).count()


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for file attachments"""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = ['id', 'filename', 'file_size', 'file_url', 'uploaded_at']
        read_only_fields = ['id', 'file_size', 'uploaded_at']

    def get_file_url(self, obj):
        """Generate signed S3 URL or direct URL"""
        if obj.file:
            # For S3: return signed URL
            # For local: return regular URL
            return obj.file.url
        return None


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying task details.
    """

    labels = TaskLabelSerializer(many=True, read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

    user_email = serializers.CharField(source='user.email', read_only=True)
    # user_avatar = serializers.SerializerMethodField()

    is_overdue = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    activity_log = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority', 'category',
            'due_date', 'estimated_duration', 'completion_percentage',
            'created_at', 'updated_at', 'completed_at', 'labels',
            'comments', 'attachments', 'user_email',
            'is_overdue', 'days_until_due','activity_log'
        ]
        read_only_fields = fields

    def get_user_avatar(self, obj):
        """Get user avatar URL"""
        # Could call User Service here
        return None

    def get_is_overdue(self, obj):
        return obj.is_overdue

    def get_days_until_due(self, obj):
        return obj.days_until_due

    def get_activity_log(self, obj):
        """Get recent activities"""
        activities = obj.activities.all()[:20]
        return TaskActivitySerializer(activities, many=True).data


class BulkTaskUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk updates (i.e. multiple records).

    Example request:
    {
        "task_ids": ["id1", "id2", "id3"],
        "status": "completed",
        "priority": "high"
    }
    """

    task_ids = serializers.ListField(
        child=serializers.UUIDField()
    )
    status = serializers.ChoiceField(
        choices=TaskStatus.choices,
        required=False
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices,
        required=False
    )
    category = serializers.CharField(required=False)

    def validate_task_ids(self, value):
        """Ensure at least one task ID"""
        if not value:
            raise serializers.ValidationError("At least one task ID required")
        if len(value) > 100:
            raise serializers.ValidationError("Cannot update more than 100 tasks")
        return value

    def validate(self, data):
        """Ensure at least one field to update"""
        if not any(data.get(field) for field in ['status', 'priority', 'category']):
            raise serializers.ValidationError(
                "At least one of: status, priority, category must be provided"
            )
        return data


class TaskStatisticsSerializer(serializers.Serializer):
    """
    Serializer for task statistics/metrics. Used to generate reports.

    Example response:
    {
        "total_tasks": 42,
        "completed_tasks": 15,
        "overdue_tasks": 2,
        "completion_rate": 35.7
    }
    """

    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    in_progress_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    average_completion_time = serializers.FloatField()
    tasks_by_priority = serializers.DictField()
    tasks_by_category = serializers.DictField()