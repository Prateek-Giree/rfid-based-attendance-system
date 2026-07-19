from django.core.exceptions import ValidationError
from django.db import models, transaction
from .models import Classroom, Student
from apps.auth_core.models import Teacher


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


class StudentService:
    """
    Service layer containing business logic for Student management.
    Handles CRUD operations, live queries, search, filter, and dashboard statistics.
    """

    @staticmethod
    @transaction.atomic
    def create_student(
        roll_no: int,
        first_name: str,
        last_name: str,
        classroom: Classroom,
        rfid_uid: str,
        guardian_name: str,
        address: str = "",
        contact: str = "",
        guardian_contact: str = "",
        is_active: bool = True,
    ) -> Student:
        """
        Registers a new student after performing model validation.
        """
        student = Student(
            roll_no=roll_no,
            first_name=first_name,
            last_name=last_name,
            classroom=classroom,
            rfid_uid=rfid_uid,
            guardian_name=guardian_name,
            address=address,
            contact=contact,
            guardian_contact=guardian_contact,
            is_active=is_active,
        )
        student.full_clean()
        student.save()
        return student

    @staticmethod
    @transaction.atomic
    def update_student(
        student: Student,
        roll_no: int,
        first_name: str,
        last_name: str,
        classroom: Classroom,
        rfid_uid: str,
        guardian_name: str,
        address: str = "",
        contact: str = "",
        guardian_contact: str = "",
        is_active: bool = True,
    ) -> Student:
        """
        Updates an existing student details.
        """
        student.roll_no = roll_no
        student.first_name = first_name
        student.last_name = last_name
        student.classroom = classroom
        student.rfid_uid = rfid_uid
        student.guardian_name = guardian_name
        student.address = address
        student.contact = contact
        student.guardian_contact = guardian_contact
        student.is_active = is_active
        
        student.full_clean()
        student.save()
        return student

    @staticmethod
    @transaction.atomic
    def delete_student(student: Student) -> None:
        """
        Performs a soft-delete on a Student instance by marking is_active=False.
        """
        student.is_active = False
        student.save()

    @staticmethod
    def search_students(queryset, q: str):
        """
        Filters students queryset by query string q across fields:
        roll_no, first_name, last_name, and rfid_uid.
        """
        if not q:
            return queryset
        return queryset.filter(
            models.Q(roll_no__icontains=q) |
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q) |
            models.Q(rfid_uid__icontains=q)
        )

    @staticmethod
    def filter_students(queryset, classroom_id: str):
        """
        Filters students queryset by classroom ID if classroom_id is provided.
        """
        if classroom_id:
            return queryset.filter(classroom_id=classroom_id)
        return queryset

    @staticmethod
    def get_student_stats(user) -> dict:
        """
        Gathers dashboard statistics:
        - Total students
        - Active students
        - Classroom distribution
        Filtered by teacher's assigned classroom(s) if user is a teacher.
        """
        if user.is_staff:
            students_qs = Student.objects.all()
            classrooms_qs = Classroom.objects.all()
        elif hasattr(user, "teacher_profile"):
            students_qs = Student.objects.filter(classroom__class_teacher=user.teacher_profile)
            classrooms_qs = Classroom.objects.filter(class_teacher=user.teacher_profile)
        else:
            students_qs = Student.objects.none()
            classrooms_qs = Classroom.objects.none()

        total_students = students_qs.count()
        active_students = students_qs.filter(is_active=True).count()

        classrooms_data = classrooms_qs.annotate(
            student_count=models.Count("students")
        ).values("name", "section", "student_count")

        students_per_classroom = [
            {
                "classroom": f"{c['name']} - {c['section']}",
                "student_count": c["student_count"]
            }
            for c in classrooms_data
        ]

        return {
            "total_students": total_students,
            "active_students": active_students,
            "students_per_classroom": students_per_classroom,
        }
