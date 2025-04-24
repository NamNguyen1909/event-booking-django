from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Cho phép đăng nhập bằng email hoặc username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        user = UserModel.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
        if not user:
            return None

        # Kiểm tra is_active trước khi xác thực
        if not user.is_active:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
