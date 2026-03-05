import django_filters
from django.utils import timezone

from .models import Task


class TaskFilter(django_filters.FilterSet):
    # Exact matches
    status = django_filters.MultipleChoiceFilter(choices=Task.Status.choices)
    priority = django_filters.MultipleChoiceFilter(choices=Task.Priority.choices)
    category = django_filters.NumberFilter(field_name="category__id")

    # Date range filters on due_date
    due_date_from = django_filters.DateTimeFilter(field_name="due_date", lookup_expr="gte")
    due_date_to = django_filters.DateTimeFilter(field_name="due_date", lookup_expr="lte")
    due_date_null = django_filters.BooleanFilter(field_name="due_date", lookup_expr="isnull")

    # Overdue shortcut
    overdue = django_filters.BooleanFilter(method="filter_overdue", label="Overdue tasks only")

    # Assignee filter
    assignee_id = django_filters.CharFilter(field_name="assignee_id", lookup_expr="exact")
    unassigned = django_filters.BooleanFilter(method="filter_unassigned")

    # Tags — pass tag=work&tag=urgent for AND match
    tag = django_filters.CharFilter(method="filter_tag", label="Tag (contains)")

    class Meta:
        model = Task
        fields = [
            "status",
            "priority",
            "category",
            "due_date_from",
            "due_date_to",
            "due_date_null",
            "overdue",
            "assignee_id",
            "unassigned",
            "tag",
        ]

    def filter_overdue(self, queryset, name, value):
        if value:
            return queryset.filter(
                due_date__lt=timezone.now()
            ).exclude(status__in=[Task.Status.DONE, Task.Status.CANCELLED])
        return queryset

    def filter_unassigned(self, queryset, name, value):
        if value:
            return queryset.filter(assignee_id="")
        return queryset.exclude(assignee_id="")

    def filter_tag(self, queryset, name, value):
        # JSONField contains lookup — works on PostgreSQL
        return queryset.filter(tags__contains=[value.lower().strip()])
