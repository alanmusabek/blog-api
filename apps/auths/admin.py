from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from .forms import UserChangeAdminForm, UserCreationAdminForm
from .models import User

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("user_header", "active_label", "staff_label", "post_count")
    list_filter = (("is_active", BooleanRadioFilter), ("is_staff", BooleanRadioFilter))
    search_fields = ("email", "first_name", "second_name")
    ordering = ("email",)
    actions = ("activate_users", "deactivate_users")
    readonly_fields = ("last_login",)
    fieldsets = (
        ("Personal info", {"classes": ("tab",), "fields": ("email", "first_name", "second_name", "password")}),
        ("Permissions", {"classes": ("tab",), "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"classes": ("tab",), "fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "first_name", "second_name", "password1", "password2")}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(post_total=Count("posts"))

    @display(description="User", ordering="email", header=True)
    def user_header(self, obj: User) -> list[str]:
        full_name = f"{obj.first_name} {obj.second_name}"
        initials = f"{obj.first_name[:1]}{obj.second_name[:1]}".upper()
        return [full_name, obj.email, initials]

    @display(description="Active", ordering="is_active", label={True: "success", False: "danger"})
    def active_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_active, "Active" if obj.is_active else "Inactive"

    @display(description="Staff", ordering="is_staff", label={True: "success", False: "warning"})
    def staff_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_staff, "Staff" if obj.is_staff else "Not staff"

    @display(description="Posts", ordering="post_total")
    def post_count(self, obj: User) -> int:
        return obj.post_total

    @action(description="Activate")
    def activate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=True)

    @action(description="Deactivate")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=False)
