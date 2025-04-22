from rest_framework import permissions

class ReviewOwner(permissions.IsAuthenticated):

    """Chỉ cho phép người dùng đã đăng nhập là chủ sở hữu của review đó mới có quyền sửa hoặc xóa review."""
    def has_object_permission(self, request, view, obj):
        return super().has_permission(request,view) and obj.user == request.user  # Kiểm tra xem người dùng có phải là chủ sở hữu của review không

class IsAdminOrOrganizer(permissions.BasePermission):
    """
    Cho phép admin và organizer tạo event.
    Organizer chỉ có thể chỉnh sửa event của mình.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'organizer')

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return obj.organizer == request.user

class IsEventOrganizer(permissions.BasePermission):
    """
    Cho phép organizer chỉ thao tác trên event của mình.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'organizer'

    def has_object_permission(self, request, view, obj):
        return obj.organizer == request.user

class IsOrganizer(permissions.BasePermission):
    """
    Cho phép organizer thực hiện các thao tác nhất định.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'organizer'

class IsEventOwnerOrAdmin(permissions.BasePermission):
    """
    Cho phép chỉnh sửa sự kiện nếu user là organizer của event hoặc admin.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'organizer')

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return obj.organizer == request.user

# Quyền chỉ cho phép quản trị viên
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'
class IsOrganizerOwner(permissions.BasePermission):
    #chp phép user là organizer và sở hữu event request.user == event.organizer
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'organizer'

    def has_object_permission(self, request, view, obj):
        return obj.organizer == request.user
    




