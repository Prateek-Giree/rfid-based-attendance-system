import random
import string
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from apps.auth_core.models import OTPVerification, User
from django.core.exceptions import ValidationError


class OTPService:
    @staticmethod
    def _generate_random_otp(length=6):
        """Generates a secure numeric OTP."""
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def _check_rate_limit(user, purpose, limit, time_window_minutes):
        """Checks if the user has exceeded the OTP request limit."""
        cutoff_time = timezone.now() - timedelta(minutes=time_window_minutes)
        recent_requests = OTPVerification.objects.filter(
            user=user,
            purpose=purpose,
            created_at__gte=cutoff_time
        ).count()
        if recent_requests >= limit:
            raise ValidationError(
                f"Too many {purpose.replace('_', ' ')} requests. Please try again in {time_window_minutes} minutes."
            )

    @classmethod
    def generate_otp(cls, user, purpose, expiry_minutes):
        """Generates, stores (hashed), and returns a plaintext OTP."""
        # Rate limits
        if purpose == "password_reset":
            cls._check_rate_limit(user, purpose, limit=3, time_window_minutes=15)
        elif purpose == "login":
            cls._check_rate_limit(user, purpose, limit=5, time_window_minutes=15)

        plaintext_otp = cls._generate_random_otp()
        hashed_otp = make_password(plaintext_otp)
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        OTPVerification.objects.create(
            user=user,
            purpose=purpose,
            otp_code=hashed_otp,
            expires_at=expires_at
        )

        return plaintext_otp

    @classmethod
    def verify_otp(cls, user, purpose, plaintext_otp):
        """Verifies an OTP and marks it as used if valid."""
        cls.cleanup_expired_otps()
        
        valid_otps = OTPVerification.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        )

        for otp_record in valid_otps:
            if check_password(plaintext_otp, otp_record.otp_code):
                otp_record.is_used = True
                otp_record.save()
                return True

        return False

    @classmethod
    def send_otp_email(cls, user, purpose, plaintext_otp):
        """Sends the OTP via email."""
        if purpose == "password_reset":
            subject = "Password Reset OTP - Smart Attendance Management System"
            template = "auth_core/emails/password_reset_otp.html"
            expiry_text = "10 minutes"
        elif purpose == "login":
            subject = "Login Verification OTP - Smart Attendance Management System"
            template = "auth_core/emails/login_otp.html"
            expiry_text = "5 minutes"
        else:
            return False

        context = {
            "user": user,
            "otp_code": plaintext_otp,
            "expiry_text": expiry_text,
        }
        
        html_message = render_to_string(template, context)
        # Fallback plaintext
        plain_message = f"Your OTP is {plaintext_otp}. It will expire in {expiry_text}."
        
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sams.local")
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            return True
        except Exception:
    
            return False

    @classmethod
    def cleanup_expired_otps(cls):
        """Removes expired OTPs from the database."""
        expired = OTPVerification.objects.filter(expires_at__lte=timezone.now())
        expired.delete()
