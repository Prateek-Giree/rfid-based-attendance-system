from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction

from ..models import Teacher

User = get_user_model()


class TeacherService:
    """
    Service layer containing business logic for Teacher management.
    Handles creation of User + Teacher profile atomically, updates,
    soft-deactivation, search, filtering, and dashboard statistics.
    """

    @staticmethod
    @transaction.atomic
    def create_teacher(
        first_name: str,
        last_name: str,
        email: str,
        contact: str,
        password: str = None,
    ) -> Teacher:
        """
        Creates a new User account and linked Teacher profile.
        If a password is provided, it hashes it using set_password().
        """
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean()
        user.save()

        teacher = Teacher(user=user, contact=contact)
        teacher.full_clean()
        teacher.save()
        return teacher

    @staticmethod
    @transaction.atomic
    def update_teacher(
        teacher: Teacher,
        first_name: str,
        last_name: str,
        email: str,
        contact: str,
        password: str = None,
    ) -> Teacher:
        """
        Updates the User fields and Teacher contact for an existing teacher.
        If a password is provided, it updates it using set_password().
        """
        user = teacher.user

        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise ValidationError("A user with this email address already exists.")

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        if password:
            user.set_password(password)
        user.full_clean()
        user.save()

        teacher.contact = contact
        teacher.full_clean()
        teacher.save()
        return teacher

    @staticmethod
    @transaction.atomic
    def deactivate_teacher(teacher: Teacher) -> None:
        """
        Soft-deactivates a teacher by setting user.is_active = False.
        Preserves all classroom assignments, attendance history, and relationships.
        """
        teacher.user.is_active = False
        teacher.user.save(update_fields=["is_active"])

    @staticmethod
    def search_teachers(queryset, q: str):
        """
        Filters teachers queryset by query string q across:
        first name, last name, email, and contact number.
        """
        if not q:
            return queryset
        return queryset.filter(
            models.Q(user__first_name__icontains=q)
            | models.Q(user__last_name__icontains=q)
            | models.Q(user__email__icontains=q)
            | models.Q(contact__icontains=q)
        )

    @staticmethod
    def get_teacher_stats(user) -> dict:
        """
        Returns dashboard statistics for the given user:
        - Admin: total_teachers, active_teachers
        - Teacher: my_classrooms_count, my_students_count
        """
        from apps.students.models import Classroom, Student

        if user.is_staff:
            from django.utils import timezone
            import datetime
            
            today = timezone.localdate()
            start_of_month = today.replace(day=1)
            
            teachers_qs = Teacher.objects.all()
            total_teachers = teachers_qs.count()
            active_teachers = teachers_qs.filter(user__is_active=True).count()
            teachers_added_this_month = teachers_qs.filter(created_at__date__gte=start_of_month).count()
            
            return {
                "total_teachers": total_teachers,
                "active_teachers": active_teachers,
                "teachers_added_this_month": teachers_added_this_month,
            }

        if hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            my_classrooms_count = Classroom.objects.filter(class_teacher=teacher).count()
            my_students_count = Student.objects.filter(
                classroom__class_teacher=teacher
            ).count()
            return {
                "my_classrooms_count": my_classrooms_count,
                "my_students_count": my_students_count,
            }

        return {
            "total_teachers": 0,
            "active_teachers": 0,
            "teachers_added_this_month": 0,
            "my_classrooms_count": 0,
            "my_students_count": 0,
        }
