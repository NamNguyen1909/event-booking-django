from rest_framework import permissions

class ReviewOwner(permissions.IsAuthenticated):

    """Chỉ cho phép người dùng đã đăng nhập là chủ sở hữu của review đó mới có quyền sửa hoặc xóa review."""
    def has_object_permission(self, request, view, obj):
        return super().has_permission(request,view) and obj.user == request.user  # Kiểm tra xem người dùng có phải là chủ sở hữu của review không

class IsAdminOrOrganizerOwner(permissions.BasePermission):
    """
    Cho phép admin và organizer tạo event.
    Organizer chỉ có thể chỉnh sửa event của mình.
    """

    def has_permission(self, request, view):
        # Cho phép admin và organizer tạo event
        if request.method == 'POST':
            return request.user.is_authenticated and request.user.role in ['admin', 'organizer']
        # Các phương thức khác yêu cầu đăng nhập
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin có quyền với tất cả các event
        if request.user.role == 'admin':
            return True
        # Organizer chỉ có quyền chỉnh sửa event của mình
        if request.user.role == 'organizer':
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return obj.organizer == request.user
            # Các phương thức khác (GET) cho phép truy cập
            return True
        # Các vai trò khác không có quyền
        return False

