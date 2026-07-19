/**
 * validators.js — SAMS Reusable Field Validators
 *
 * Pure functions only. No DOM access.
 * Each function returns { valid: boolean, message: string }.
 */

const PHONE_REGEX = /^(97|98)\d{8}$/;
const NAME_REGEX = /^[a-zA-Z\s]+$/;

/**
 * Checks that a value is non-empty after trimming.
 */
function validateRequired(value) {
    if (!value || value.trim() === "") {
        return { valid: false, message: "This field is required." };
    }
    return { valid: true, message: "" };
}

/**
 * Checks basic email format.
 */
function validateEmail(value) {
    if (!value || value.trim() === "") {
        return { valid: false, message: "Email address is required." };
    }
    const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!EMAIL_REGEX.test(value.trim())) {
        return { valid: false, message: "Enter a valid email address." };
    }
    return { valid: true, message: "" };
}

/**
 * Validates a Nepali phone number.
 * Rules: exactly 10 digits, must start with 97 or 98.
 * @param {boolean} required - if false, empty values pass.
 */
function validatePhone(value, required = true) {
    const trimmed = value ? value.trim() : "";
    if (trimmed === "") {
        if (required) {
            return { valid: false, message: "Contact number is required." };
        }
        return { valid: true, message: "" };
    }
    if (!PHONE_REGEX.test(trimmed)) {
        return {
            valid: false,
            message: "Enter a valid 10-digit number starting with 97 or 98.",
        };
    }
    return { valid: true, message: "" };
}

/**
 * Validates a name field (letters and spaces only).
 * @param {number} min - minimum length (default 2)
 * @param {number} max - maximum length (default 50)
 */
function validateName(value, min = 2, max = 50) {
    const trimmed = value ? value.trim() : "";
    if (trimmed === "") {
        return { valid: false, message: "This field is required." };
    }
    if (trimmed.length < min) {
        return { valid: false, message: `Must be at least ${min} characters.` };
    }
    if (trimmed.length > max) {
        return { valid: false, message: `Must be no more than ${max} characters.` };
    }
    if (!NAME_REGEX.test(trimmed)) {
        return { valid: false, message: "Only letters and spaces are allowed." };
    }
    return { valid: true, message: "" };
}

/**
 * Validates an RFID UID.
 * Rules: 4–50 characters, non-empty.
 */
function validateRFID(value) {
    const trimmed = value ? value.trim() : "";
    if (trimmed === "") {
        return { valid: false, message: "RFID UID is required." };
    }
    if (trimmed.length < 4) {
        return { valid: false, message: "RFID UID must be at least 4 characters." };
    }
    if (trimmed.length > 50) {
        return { valid: false, message: "RFID UID must be no more than 50 characters." };
    }
    return { valid: true, message: "" };
}

/**
 * Validates a roll number.
 * Rules: integer, min=1, max=9999.
 */
function validateRollNo(value) {
    const trimmed = value ? String(value).trim() : "";
    if (trimmed === "") {
        return { valid: false, message: "Roll number is required." };
    }
    const num = parseInt(trimmed, 10);
    if (isNaN(num) || !Number.isInteger(num)) {
        return { valid: false, message: "Roll number must be a whole number." };
    }
    if (num < 1) {
        return { valid: false, message: "Roll number must be at least 1." };
    }
    if (num > 9999) {
        return { valid: false, message: "Roll number cannot exceed 9999." };
    }
    return { valid: true, message: "" };
}

/**
 * Validates a plain text length (no character-type enforcement).
 * @param {boolean} required
 * @param {number} min
 * @param {number} max
 */
function validateLength(value, required = false, min = 0, max = 500) {
    const trimmed = value ? value.trim() : "";
    if (trimmed === "") {
        if (required) {
            return { valid: false, message: "This field is required." };
        }
        return { valid: true, message: "" };
    }
    if (min > 0 && trimmed.length < min) {
        return { valid: false, message: `Must be at least ${min} characters.` };
    }
    if (trimmed.length > max) {
        return { valid: false, message: `Must be no more than ${max} characters.` };
    }
    return { valid: true, message: "" };
}

/**
 * Validates a password field.
 * Rules: minimum 8 characters.
 * @param {boolean} required
 */
function validatePassword(value, required = true) {
    const trimmed = value ? value : "";
    if (trimmed === "") {
        if (required) {
            return { valid: false, message: "Password is required." };
        }
        return { valid: true, message: "" };
    }
    if (trimmed.length < 8) {
        return { valid: false, message: "Password must be at least 8 characters." };
    }
    return { valid: true, message: "" };
}

/**
 * Validates that two password fields match.
 * @param {string} password - the primary password value
 * @param {string} confirmPassword - the confirm password value
 * @param {boolean} required
 */
function validatePasswordMatch(password, confirmPassword, required = true) {
    if (!confirmPassword || confirmPassword === "") {
        if (required || (password && password !== "")) {
            return { valid: false, message: "Please confirm your password." };
        }
        return { valid: true, message: "" };
    }
    if (password !== confirmPassword) {
        return { valid: false, message: "Passwords do not match." };
    }
    return { valid: true, message: "" };
}
