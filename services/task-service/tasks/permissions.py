from rest_framework import permissions


class IsTaskOwner(permissions.BasePermission):
    """
    Permission to check if user is the task owner.
    Only allows task owners to edit/delete their own tasks.
    """

    message = "You can only edit your own tasks."

    def has_object_permission(self, request, view, obj):
        """
        Checks if user has necessary read/write permissions.
        """
        # Read permissions for authenticated user
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user

        # Write permissions for task owners only
        return obj.user == request.user


class IsCommentAuthor(permissions.BasePermission):
    """
    Permission to check if user is the comment author.
    """

    message = "You can only edit your own comments."

    def has_object_permission(self, request, view, obj):
        # Read permissions allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions for authors only
        return obj.author == request.user


class IsLabelOwner(permissions.BasePermission):
    """
    Permission to check if user owns the label.
    """

    message = "You can only use your own labels."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user