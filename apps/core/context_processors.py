def user_role(request):
    """
    Injects role flags into every template context.
    Available in all templates as: is_admin, is_teacher, user_role
    """
    if not request.user.is_authenticated:
        return {
            "is_admin": False,
            "is_teacher": False,
            "user_role": "anonymous",
        }

    is_admin = request.user.is_staff
    is_teacher = not is_admin and hasattr(request.user, "teacher_profile")

    return {
        "is_admin": is_admin,
        "is_teacher": is_teacher,
        "user_role": "admin" if is_admin else ("teacher" if is_teacher else "none"),
    }
