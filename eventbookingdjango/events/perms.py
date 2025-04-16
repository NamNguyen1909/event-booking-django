from rest_framework import permissions

class ReviewOwner(permissions.IsAuthenticated):

    """Chỉ cho phép người dùng đã đăng nhập là chủ sở hữu của review đó mới có quyền sửa hoặc xóa review."""
    def has_object_permission(self, request, view, obj):
        return super().has_permission(request,view) and obj.user == request.user  # Kiểm tra xem người dùng có phải là chủ sở hữu của review không