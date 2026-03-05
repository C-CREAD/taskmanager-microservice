from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTaskOwner(BasePermission):
    """
    Allow access only to the owner of the task.
    Safe methods (GET, HEAD, OPTIONS) are also allowed to assignees.
    """
    message = "You do not have permission to modify this task."

    def has_object_permission(self, request, view, obj):
        user_id = str(request.user.id)

        # Owners have full access
        if obj.owner_id == user_id:
            return True

        # Assignees can read (and update status only — enforced in the view)
        if request.method in SAFE_METHODS and obj.assignee_id == user_id:
            return True

        return False
