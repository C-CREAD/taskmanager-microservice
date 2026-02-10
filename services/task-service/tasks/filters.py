# filters.py
import django_filters
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import Task, TaskStatus, TaskPriority


class TaskFilterSet(django_filters.FilterSet):
    """
    FilterSet for Task filtering and searching.

    • Filter types:
        - status
        - priority
        - category
        - due_date (before/after)
        - created_at (before/after)
        - has_labels/has_comments/has_due_date/is_overdue

    • Search types:
        - search (by different fields, e.g. title)
        - labels
    """

    status = django_filters.MultipleChoiceFilter(
        choices=TaskStatus.choices,
        help_text="Filter by task status"
    )

    priority = django_filters.MultipleChoiceFilter(
        choices=TaskPriority.choices,
        help_text="Filter by task priority"
    )

    category = django_filters.CharFilter(
        lookup_expr='iexact',  # Case-insensitive
        help_text="Filter by category name"
    )

    due_date_after = django_filters.DateTimeFilter(
        field_name='due_date',
        lookup_expr='gte',
        help_text="Filter tasks due after this date"
    )

    due_date_before = django_filters.DateTimeFilter(
        field_name='due_date',
        lookup_expr='lte',
        help_text="Filter tasks due before this date"
    )

    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    has_labels = django_filters.BooleanFilter(
        method='filter_has_labels'
    )

    has_comments = django_filters.BooleanFilter(
        method='filter_has_comments'
    )

    has_due_date = django_filters.BooleanFilter(
        method='filter_has_due_date'
    )

    is_overdue = django_filters.BooleanFilter(
        method='filter_is_overdue'
    )

    search = django_filters.CharFilter(
        method='filter_search',
        help_text="Search in title and description"
    )

    label_name = django_filters.CharFilter(
        field_name='labels__name',
        lookup_expr='iexact'
    )

    class Meta:
        model = Task
        fields = []

    def filter_has_labels(self, queryset, name, value):
        """Filter tasks by whether they have labels"""
        if value:
            return queryset.filter(labels__isnull=False).distinct()
        return queryset.filter(labels__isnull=True).distinct()

    def filter_has_comments(self, queryset, name, value):
        """Filter tasks by whether they have comments"""
        if value:
            return queryset.annotate(
                comment_count=Count('comments')
            ).filter(comment_count__gt=0)
        return queryset

    def filter_has_due_date(self, queryset, name, value):
        """Filter tasks by whether they have a due date"""
        if value:
            return queryset.filter(due_date__isnull=False)
        return queryset.filter(due_date__isnull=True)

    def filter_is_overdue(self, queryset, name, value):
        """Filter overdue tasks thar are not completed"""
        if value:
            return queryset.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            )
        return queryset

    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields.

        Queries:
        - Title (starts with, contains)
        - Description
        - Category
        - Labels
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(category__icontains=value) |
            Q(labels__name__icontains=value)
        ).distinct()