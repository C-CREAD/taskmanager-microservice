from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from uuid import uuid4


class TaskStatus(models.TextChoices):
    ASSIGNED = 'assigned', 'Assigned'
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    ON_HOLD = 'on_hold', 'On Hold'


class TaskPriority(models.TextChoices):
    LOW = 'low', 'P3 (Low)'
    MEDIUM = 'medium', ' P2 (Medium)'
    HIGH = 'high', 'P1 (High)'
    CRITICAL = 'critical', 'P0 (Critical)'


class Task(models.Model):
    """
    Task model representing a single task in the system.

    • Task information
        - id: UUID (i.e. Task ID) Primary key to uniquely identify Task record
        - user_id: Foreign key to identify Task owner
        - title: Task title for general identification
        - status: Check Task's progress
        - priority: Helps with filtering and sorting based Task's urgency
        - due_date: Task due date, also required for reminder scheduling
        - estimated_duration: Context of (minimum) time required to complete task
        - completion_percentage: Context on Task's completion progress as a percentage

    • Categorization information
        - category/labels: Task category and labels for group association, helps with organization.

    • Audit information
        - created_at/updated_at/completed_at: Audit trail for Task activities
        - is_deleted: Soft delete for audit compliance (30 days minimum before permanent deletion)

    • Notification information
        - reminder_sent: Check if notification for Task's due date reminder is sent
        - overdue_notification_sent: Check if notification for Task's overdue reminder is sent
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text='Task owner'
    )
    title = models.CharField(
        max_length=255,
        help_text='Task title'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed description about the task'
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
        help_text='Current task status, e.g., In Progress'
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM, db_index=True,
        help_text='Task priority from Low - Critical'
    )
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text='Due date of the task to be completed'
    )
    estimated_duration = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text = "Estimated time in minutes",
    )
    completion_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="How far the task is completed between 0 - 100%"
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Task category for grouping'
    )
    labels = models.ManyToManyField(
        'TaskLabel',
        related_name='tasks',
        blank=True,
        help_text='Custom task labels/tags'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True
    )
    is_deleted = models.BooleanField( # Soft delete
        default=False,
        db_index=True,
        help_text="Soft delete check"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Date when task was completed"
    )

    reminder_sent = models.BooleanField(
        default=False,
        help_text="Checks if reminder email was sent"
    )
    overdue_notification_sent = models.BooleanField(
        default=False,
        help_text="Check if overdue notification was sent"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['user', 'priority']),
        ]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != TaskStatus.COMPLETED:
            return timezone.now() > self.due_date
        return False

    @property
    def days_until_due(self):
        """Calculate days until due date"""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None

    def mark_completed(self):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = timezone.now()
        self.completion_percentage = 100
        self.save()

    def mark_in_progress(self):
        """Mark task as in progress"""
        self.status = TaskStatus.IN_PROGRESS
        self.save(update_fields=['status', 'updated_at'])

    def mark_cancelled(self):
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    def soft_delete(self):
        """Soft delete task (keeps for audit)"""
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])


class TaskComment(models.Model):
    """
    Task Comment Model representing a task comment on a given Task.
    Included for team collaboration, audit trail on changes and activities,
    and enabled notifications when commented on.

    • Comment information
        - id: UUID (i.e. Comment ID) Primary key to uniquely identify Comment record
        - task: Foreign key to identify Task to associate the comment with
        - author: Foreign key to identify Task author (User)
        - content: Task Comment containing general information.

    • Audit information
        - created_at/updated_at: Audit trail for Task Comments
        - is_deleted: Soft delete for audit compliance (30 days minimum before permanent deletion)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments'
    )

    content = models.TextField(help_text="Comment text")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete check"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "Task Comment"
        verbose_name_plural = "Task Comments"

    def __str__(self):
        return f"Comment on {self.task.title} by {self.author.username}"


class TaskLabel(models.Model):
    """
    Task Label Model representing reusable labels for task categorization.

    • Label information
        - id: UUID (i.e. Label ID) Primary key to uniquely identify Label record
        - user: Foreign key to identify User
        - name: Task Label name for general labeling.
        - color: Hex color for Task Label for better customization

    • Audit information
        - created_at/updated_at/: Audit trail for Task Labels
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_labels'
    )
    name = models.CharField(
        max_length=100,
        help_text="Label name (e.g., 'bug', 'feature')"
    )
    color = models.CharField(
        max_length=7,
        default='#808080',   # Hex color
        help_text = "Hex color code"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')
        verbose_name = "Task Label"
        verbose_name_plural = "Task Labels"

    def __str__(self):
        return self.name


class TaskActivity(models.Model):
    """
    Task Activity Model representing an audit log for task changes.
    All records are immutable for compliance & debugging, and
    notifications are triggered per activity

    • Activity information
        - id: UUID (i.e. Activity ID) Primary key to uniquely identify Activity record
        - task: Foreign key to identify Task

    • Audit information
        (What changed)
            - field_name: Track the field name that was changed (e.g., status, priority, etc.)
            - old_value: Get the old field value before the change
            - new_value: Get the new field value after the change
        (Who changed it and When)
            - changed_by: Foreign key to identify User, track user who made changes
            - changed_at: Track date and time of changes made
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    field_name = models.CharField(
        max_length=100,
        help_text="Field Name: e.g., 'status', 'priority', 'title'"
    )
    old_value = models.TextField(help_text="Previous value")
    new_value = models.TextField(help_text="New value")

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_activity_changes'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Task Activity"
        verbose_name_plural = "Task Activities"
        get_latest_by = 'change_at'

    def __str__(self):
        return f"{self.task.title}: {self.field_name} changed"


class TaskAttachment(models.Model):
    """
    Tech Attachment Model that represents file attachment(s) for tasks.
    Provides additional context for tasks through documents, pictures, and files.
    Intended to be stored in AWS S3 for scalability. (future reference)

    • Attachment information
        - id: UUID (i.e. Attachment ID) Primary key to uniquely identify Attachment record
        - task: Foreign key to identify Task
        - file: File attachment for Task
        - filename: File name of attachment
        - file_size: File size of attachment in bytes

    • Audit information
        - uploaded_by: Foreign key to identify User, track user that uploaded attachment
        - uploaded_at: Track date and time of changes made
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    file = models.FileField(
        upload_to='tasks/%Y/%m/%d/',
        help_text="File path in AWS S3"
    )
    filename = models.CharField(
        max_length=255,
        help_text="File Name"
    )
    file_size = models.IntegerField(help_text="File size in bytes")

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Who uploaded the file"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Task Attachment"
        verbose_name_plural = "Task Attachments"

    def __str__(self):
        return f"{self.filename} on {self.task.title}"

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return self.file_size / (1024 * 1024)


old_values = {}


@receiver(pre_save, sender=Task)
def get_old_values(sender, instance, **kwargs):
    """
    Get the old values of a task before it gets updated.
    """
    if instance.pk:  # Only for existing tasks (updates)
        try:
            old = Task.objects.get(pk=instance.pk)
            old_values[instance.pk] = {
                'title': old.title,
                'user': old.user,
                'description': old.description,
                'status': old.status,
                'priority': old.priority,
                'category': old.category,
                'labels': old.labels,
                'due_date': old.due_date,
                'estimated_duration': old.estimated_duration,
                'completion_percentage': old.completion_percentage,
                'created_at': old.created_at,
                'updated_at': old.updated_at,
                'completed_at': old.completed_at,

                # Add other fields you want to track
            }
        except Task.DoesNotExist:
            old_values[instance.pk] = {}


@receiver(post_save, sender=Task)
def create_activity_on_task_change(sender, instance, created, **kwargs):
    """
    Create an activity log entry when task is created or updated.
    Used to maintain an immutable audit log.
    """

    if created:
        TaskActivity.objects.create(
            task=instance,
            field_name='created',
            old_value='',
            new_value=f'Task created: {instance.title}',
            changed_by=None  # System created
        )
    else:
        # Remove any existing values
        old_values.pop(instance.pk, {})

        for field_name in old_values:
            new_value = instance.field_name
            old_value = old_values.get(field_name)

            if new_value != old_value:
                TaskActivity.objects.create(
                    task=instance,
                    field_name=f'{field_name} updated',
                    old_value=f'Before Update: {old_value}',
                    new_value=f'After Update: {new_value}',
                    changed_by=instance.user
                )


@receiver(pre_delete, sender=Task)
def create_activity_on_task_delete(sender, instance, **kwargs):
    """Create activity log when task is deleted"""
    TaskActivity.objects.create(
        task=instance,
        field_name='is_deleted',
        old_value=f'Task "{instance.title}" existed',
        new_value='Task marked for deletion',
        changed_by=instance.user
    )


@receiver(post_save, sender=TaskComment)
def notify_on_task_comment(sender, instance, created, **kwargs):
    """
    Send a notification when task is commented on.
    """
    # if created:
    #     from .tasks import send_comment_notification
    #
    #     # Queue async notification
    #     send_comment_notification.delay(instance.id)
    pass


class TaskQuerySet(models.QuerySet):
    """Custom QuerySet with optimization methods"""

    def with_related(self):
        """Optimize with all related data"""
        return (self.select_related('user')
        .prefetch_related(
            'labels',
            'comments__author',
            'attachments__uploaded_by',
            'activities__changed_by'
        ))

    def active(self):
        """Only non-deleted tasks"""
        return self.filter(is_deleted=False)

    def for_user(self, user):
        """Tasks for specific user"""
        return self.filter(user=user)

    def overdue(self):
        """Only overdue tasks"""
        return self.filter(
            due_date__lt=timezone.now(),
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        )

    def due_soon(self, hours=24):
        """Tasks due within 24 hours"""
        cutoff = timezone.now() + timezone.timedelta(hours=hours)
        return self.filter(
            due_date__range=[timezone.now(), cutoff],
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        )

    def completed(self):
        """Only completed tasks"""
        return self.filter(status=TaskStatus.COMPLETED)

    def by_priority(self, priority):
        """Filter by priority"""
        return self.filter(priority=priority)

    def user_tasks(self, user):
        return self.for_user(user).active().with_related()


class TaskManager(models.Manager):
    """Custom manager for Task"""

    def get_queryset(self):
        return TaskQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def active(self):
        return self.get_queryset().active()

    def overdue(self):
        return self.get_queryset().overdue()

    def due_soon(self, hours=24):
        return self.get_queryset().due_soon(hours)

    def user_tasks(self, user):
        return self.get_queryset().user_tasks(user)


# Attach custom manager to Task
# Task.objects = TaskManager()