from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from .models import Task, TaskComment, TaskActivity


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
    """Create activity log when task is created or updated"""

    if created:
        TaskActivity.objects.create(
            task=instance,
            field_name='created',
            old_value='',
            new_value=f'Task created',
            changed_by=instance.user
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
def create_activity_on_comment(sender, instance, created, **kwargs):
    """Create activity log when comment is added"""
    if created:
        TaskActivity.objects.create(
            task=instance.task,
            field_name='comment',
            old_value='',
            new_value=f'Comment added by {instance.created_by}',
            changed_by=instance.created_by
        )

        # Also send notification (your existing code)
        # from .tasks import send_comment_notification
        # send_comment_notification.delay(instance.id)


@receiver(pre_delete, sender=TaskComment)
def create_activity_on_comment_delete(sender, instance, **kwargs):
    """Create activity log when comment is deleted"""
    TaskActivity.objects.create(
        task=instance.task,
        field_name=f'Content: {instance.content}',
        old_value=f'Comment by {instance.author} existed',
        new_value=f'Comment deleted at {instance.updated_at}',
        changed_by=instance.author
    )

@receiver(post_save, sender=TaskComment)
def notify_on_comment(sender, instance, created, **kwargs):
    """Send notification when task is commented on"""

    # if created:
    #     from .tasks import send_comment_notification
    #
    #     # Queues async notification
    #     send_comment_notification.delay(instance.id)

    pass