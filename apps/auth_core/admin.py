from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import User, Teacher,OTPVerification

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
    )

    ordering = ("email",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass


@admin.register(Teacher)
class TeacherAdmin(ModelAdmin):
    list_display = (
        "get_full_name",
        "get_email",
        "contact",
        "created_at",
    )

    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "contact",
    )

    list_filter = ("created_at",)

    ordering = (
        "user__first_name",
        "user__last_name",
    )

    list_per_page = 20

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Email")
    def get_email(self, obj):
        return obj.user.email

@admin.register(OTPVerification)
class OTPVerificationAdmin(ModelAdmin):
    list_display = (
        "user",
        "purpose",
        "created_at",
        "expires_at",
        "is_used",
    )

    search_fields = (
        "user__email",
        "purpose",
    )

    list_filter = (
        "purpose",
        "is_used",
        "created_at",
    )

    ordering = ("-created_at",)

    list_per_page = 20