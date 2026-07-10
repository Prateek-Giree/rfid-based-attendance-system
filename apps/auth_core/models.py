from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Teacher(models.Model):
    user = models.OneToOneField(
        "auth_core.User",
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    contact = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.email