from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import timedelta
import requests

from .models import Task, TaskActivity
from django.contrib.auth.models import User

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name='tasks.send_due_date_reminder')
def send_due_date_reminder(self, task_id):
    """
    Send reminder email when task is due soon (i.e. 24 hours).
    If sending fails, retry 3 times every [60, 120, 240] seconds
    """

    # Validating email logic before sending email
    try:
        logger.info(f"Sending reminder for task {task_id}")

        task = Task.objects.get(id=task_id)

        # Don't send email if task is already sent or already completed
        if task.reminder_sent or task.status == Task.TaskStatus.COMPLETED:
            logger.info(f"Task {task_id} already has reminder sent, skipping")
            return {'status': 'skipped', 'reason': 'already_sent/completed'}

        # Check if task due date is within 24 hours
        if task.due_date:
            hours_until_due = (task.due_date - timezone.now()).total_seconds() / 3600
            if hours_until_due > 24:
                logger.info(f"Task {task_id} due in {hours_until_due:.1f} hours, skipping")
                return {'status': 'skipped', 'reason': 'due_soon'}

        user = task.user

        # Email template
        subject = f"Reminder: {task.title} is due soon"
        html_message = render_to_string('task_reminder_email.html', {
            'task': task,
            'user': user,
            'due_in': task.days_until_due
        })

        try:
            # Send email via Notification Service
            response = requests.post(
                'http://notification-service:8003/api/notifications/send-email',
                json={
                    'user_id': str(user.id),
                    'email': user.email,
                    'subject': subject,
                    'html_message': html_message,
                    'task_id': str(task.id),
                    'notification_type': 'task_reminder'
                },
                timeout=10
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Notification service returned: {response.status_code}")
        except Exception as e:
            logger.error(f"Notification service error: {e}")
            raise self.retry(e=e, countdown=60 * (2 ** self.request.retries))

        # Mark task reminder as sent
        task.reminder_sent = True
        task.save(update_fields=['reminder_sent', 'updated_at'])

        logger.info(f"✅ Reminder sent for task {task_id}")
        return {'status': 'success'}

    except Task.DoesNotExist:
        logger.warning(f"Task {task_id} not found")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as e:
        logger.error(f"Error sending due soon reminder: {e}")
        return self.retry(e=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, name='tasks.send_overdue_notification')
def send_overdue_notification(self, task_id):
    """
    Send notification when task becomes overdue.
    If sending fails, retry 3 times every 5-minute
    """

    # Validate notification logic before sending notifications
    try:
        logger.info(f"Checking overdue status for task {task_id}")

        task = Task.objects.get(id=task_id)

        # Do not send if already notified, completed, or no due date
        if task.overdue_notification_sent or task.status == Task.TaskStatus.COMPLETED or not task.due_date:
            return {'status': 'skipped', 'reason': 'already_sent/completed/no_due_date'}

        # Do not send if task is not overdue
        if timezone.now() <= task.due_date:
            logger.info(f"Task {task_id} is not yet overdue")
            return {'status': 'skipped', 'reason': 'not_overdue'}

        user = task.user

        # Send notification via Notification Service
        subject = f"⚠️ Task Overdue: {task.title}"
        html_message = render_to_string('task_overdue_email.html', {
            'task': task,
            'days_overdue': abs(task.days_until_due)
        })

        try:
            # Send email via Notification Service
            response = requests.post(
                'http://notification-service:8003/api/notifications/send-email',
                json={
                    'user_id': str(user.id),
                    'email': user.email,
                    'subject': subject,
                    'html_message': html_message,
                    'task_id': str(task.id),
                    'notification_type': 'task_reminder',
                    'priority': 'high'
                },
                timeout=10
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Notification service returned: {response.status_code}")
        except Exception as e:
            logger.error(f"Notification service error: {e}")
            raise self.retry(e=e, countdown=60 * (2 ** self.request.retries))

        # Mark task reminder as sent
        task.overdue_notification_sent = True
        task.save(update_fields=['overdue_notification_sent'])

        logger.info(f"✅ Overdue notification sent for task {task_id}")
        return {'status': 'success'}

    except Task.DoesNotExist:
        logger.warning(f"Task {task_id} not found")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as e:
        logger.error(f"Error sending overdue reminder: {e}")
        return self.retry(e=e, countdown=300)


@shared_task(bind=True, max_retries=2, name='tasks.generate_task_report')
def generate_task_report(self, user_id, period='month'):
    """
    Generates a task completion report for the user, then is sent to Analytics Service.
    If sending fails, retry 2 times every 10 minutes

    • Future Reference
        - Report can be exported into a PDF
        - Report will be uploaded to AWS S3
    """

    try:
        logger.info(f"Generating {period} report for user {user_id}")

        user = User.objects.get(id=user_id)

        # Calculate date range
        end_date = timezone.now()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)

        # Query task metrics
        tasks = Task.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        )

        completed = tasks.filter(status=Task.TaskStatus.COMPLETED).count()
        total = tasks.count()
        completion_rate = (completed / total * 100) if total > 0 else 0

        report_data = {
            'user': user.email,
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': completion_rate,
            'average_days_to_complete': calculate_avg_completion_time(tasks)
        }

        try:
            # Send report to Analytics Service
            response = requests.post(
                'http://analytics-service:8004/api/analytics/store-report',
            json={
                'user_id': str(user.id),
                'report_data': report_data,
                'period': period
            },
            timeout=30
            )

            if response.status_code not in [200, 201]:
                raise Exception(f"Analytics service returned: {response.status_code}")
        except Exception as e:
            logger.error(f"Notification service error: {e}")
            raise self.retry(e=e, countdown=60 * (2 ** self.request.retries))

        # Mark report as sent
        logger.info(f"✅ Report generated and sent for user {user_id}")
        return {'status': 'success','report_data': report_data}

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise self.retry(exc=e, countdown=600)


@shared_task(bind=True, max_retries=2, name='tasks.bulk_update_tasks')
def bulk_update_tasks(self, user_id, task_ids, updates):
    """
    Performs bulk update on multiple tasks.

    Updates can include:
    - status
    - priority
    - category
    - labels
    """

    # Validating bulk update logic before performing update operations to the database
    try:
        logger.info(f"Bulk updating {len(task_ids)} tasks for user {user_id}")

        # Check if user is logged in first
        user = User.objects.get(id=user_id)

        # Get tasks belonging to user only
        tasks = Task.objects.filter(
            id__in=task_ids,
            user=user,
            is_deleted=False
        )

        updated_count = 0

        # Get old values
        for task in tasks:
            old_values = {
                'status': task.status,
                'priority': task.priority,
                'category': task.category
            }

            # Update new values
            for field, value in updates.items():
                if hasattr(task, field) and value is not None:
                    setattr(task, field, value)

            task.save()
            updated_count += 1

            # Log activity for each task
            for field, old_value in old_values.items():
                new_value = getattr(task, field)
                if old_value != new_value:
                    TaskActivity.objects.create(
                        task=task,
                        field_name=field,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        changed_by=user
                    )

        logger.info(f"✅ Updated {updated_count} tasks")
        return {'status':'success', 'updated_count': updated_count}

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'status': 'error', 'reason': 'not_found'}
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise self.retry(exc=e, countdown=300)



@shared_task(name='tasks.cleanup_deleted_tasks', rate_limit='10/m')
def cleanup_deleted_tasks():
    """
    Performs hard-delete on soft-deleted tasks after 30 days. Deletes 10 tasks per minute
    Keeps database clean while maintaining soft-delete grace period.
    """

    # Validate deletion logic before perform delete operation on database
    try:
        cutoff_date = timezone.now() - timedelta(days=30)

        deleted_tasks = Task.objects.filter(
            is_deleted=True,
            updated_at__lt=cutoff_date
        )

        count = deleted_tasks.count()
        deleted_tasks.delete()

        # Mark deleted tasks
        logger.info(f"✅ Cleaned up {count} old deleted tasks")
        return {'status:': 'success','cleaned_up': count}

    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return {'status': 'error'}


def calculate_avg_completion_time(tasks):
    """Calculate average days to complete tasks"""
    completed = tasks.filter(
        status=Task.TaskStatus.COMPLETED,
        completed_at__isnull=False
    )
    if not completed.exists():
        return 0

    total_days = sum([(t.completed_at - t.created_at).days for t in completed])
    return round(total_days / completed.count(), 1)