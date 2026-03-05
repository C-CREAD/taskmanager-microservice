from django.db import models


class Category(models.Model):
    """
    Task categories are global (shared across all users) or
    can be extended to be per-user by adding an owner_id field.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    color = models.CharField(
        max_length=7,
        default="#6b7280",
        help_text="Hex color code, e.g. #3b82f6",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Icon name or emoji for UI display",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
