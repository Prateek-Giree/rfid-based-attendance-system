from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Classroom


class ClassroomService:
    """
    Service layer containing business logic for Classroom management.
    Ensures thin views and proper isolation of domain rules.
    """

    @staticmethod
    @transaction.atomic
    def create_classroom(name: str, section: str, class_teacher=None) -> Classroom:
        """
        Creates a new Classroom instance after performing model validation.
        """
        classroom = Classroom(
            name=name,
            section=section,
            class_teacher=class_teacher,
        )
        classroom.full_clean()
        classroom.save()
        return classroom

    @staticmethod
    @transaction.atomic
    def update_classroom(classroom: Classroom, name: str, section: str, class_teacher=None) -> Classroom:
        """
        Updates an existing Classroom instance after performing model validation.
        """
        classroom.name = name
        classroom.section = section
        classroom.class_teacher = class_teacher
        classroom.full_clean()
        classroom.save()
        return classroom

    @staticmethod
    @transaction.atomic
    def delete_classroom(classroom: Classroom) -> None:
        """
        Deletes a Classroom instance.
        Business Rule: Prevent deletion if there are registered students or associated devices.
        """
        if classroom.students.exists():
            raise ValidationError(
                "Cannot delete classroom because it has registered students."
            )

        if classroom.devices.exists():
            raise ValidationError(
                "Cannot delete classroom because it has associated RFID devices."
            )

        classroom.delete()
