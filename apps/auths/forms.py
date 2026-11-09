from unfold.forms import UserChangeForm, UserCreationForm

from .models import User


class UserChangeAdminForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class UserCreationAdminForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "second_name")
