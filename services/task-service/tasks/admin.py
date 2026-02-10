from django.contrib import admin
from django.utils.html import format_html
from .models import Task, TaskComment, TaskLabel, TaskActivity, TaskAttachment


class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'status', 'priority', 'due_date',
                    'completion_percentage', 'category', 'created_at', )
    list_filter = ('user', 'status', 'priority', 'due_date', 'category', 'labels', 'is_deleted', )
    search_fields = ('title', 'description', 'category', 'labels', 'user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at', )

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'user')
        }),
        ('Task Details', {
            'fields': ('status', 'priority', 'category', 'labels')
        }),
        ('Scheduling', {
            'fields': ('due_date', 'estimated_duration')
        }),
        ('Progress', {
            'fields': ('completion_percentage', 'completed_at')
        }),
        ('Reminders', {
            'fields': ('reminder_sent', 'overdue_notification_sent')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_deleted'),
            'classes': ('collapse',)
        })
    )


class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'author', 'content', 'created_at', )
    list_filter = ('updated_at', 'author', 'is_deleted', )
    search_fields = ('task__title', 'author__username', 'content', )
    readonly_fields = ('id', 'created_at', 'updated_at', )
    fieldsets = (
        ('Comment', {
            'fields': ('id', 'task', 'author', 'content')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_deleted')
        })
    )


class TaskLabelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'color_preview','created_at', )
    list_filter = ('created_at', 'user', )
    search_fields = ('name', 'user__username', )
    readonly_fields = ('id', 'created_at', 'updated_at', )

    def color_preview(self, obj):
        """Display color preview"""
        return format_html(
            '<div style="width: 30px; height: 30px; background-color: {}; '
            'border: 1px solid #ddd; border-radius: 3px;"></div>',
            obj.color
        )

    color_preview.short_description = 'Color'


class TaskActivityAdmin(admin.ModelAdmin):
    list_filter = ('id', 'task', 'field_name', 'changed_by', 'changed_at', )
    list_filter = ('field_name', 'changed_by', 'changed_at', )
    search_fields = ('task__title', 'field_name', 'changed_by__username', )
    readonly_fields = ('id', 'task', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at',)

    fieldsets = (
        ('Activity Details', {
            'fields': ('id', 'task', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at')
        }),
    )


class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'file_size_display', 'uploaded_by', 'uploaded_at', )
    list_filter = ('uploaded_at', 'uploaded_by', )
    search_fields = ('filename', 'task__title', 'uploaded_by__username', )
    readonly_fields = ('id', 'uploaded_at', )

    fieldsets = (
        ('File', {
            'fields': ('id', 'task', 'file', 'filename', 'file_size', 'uploaded_by', 'uploaded_at')
        }),
    )

    def file_size_display(self, obj):
        """Display file size in a readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    file_size_display.short_description = 'File Size'


admin.site.register(Task, TaskAdmin)
admin.site.register(TaskComment, TaskCommentAdmin)
admin.site.register(TaskLabel, TaskLabelAdmin)
admin.site.register(TaskActivity, TaskActivityAdmin)
admin.site.register(TaskAttachment, TaskAttachmentAdmin)