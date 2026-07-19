/**
 * form-validation.js — SAMS Client-Side Form Validation Orchestrator
 *
 * Responsibilities:
 *  - Attach blur handlers for per-field validation feedback
 *  - Attach submit handler to block submission on invalid data
 *  - Render inline error / success states using Tailwind classes
 *  - Re-initialise after HTMX partial swaps
 *
 * Convention:
 *  Add data-validator="<type>" to any input/textarea/select to opt in.
 *  Add data-required="true" to mark the field as required.
 *  Add data-match-field="<input-id>" on password-confirm fields.
 *  Add data-min="<n>" and data-max="<n>" to override length defaults.
 *  Add data-phone-optional="true" for optional phone fields.
 */

// ── CSS state class names (must match base.html component definitions) ────────

const CSS_ERROR   = "input-error-state";
const CSS_SUCCESS = "input-success-state";

// ── DOM helpers ───────────────────────────────────────────────────────────────

function getErrorEl(input) {
    return input.parentElement.querySelector("[data-validation-error]");
}

function showFieldError(input, message) {
    input.classList.remove(CSS_SUCCESS);
    input.classList.add(CSS_ERROR);

    let errorEl = getErrorEl(input);
    if (!errorEl) {
        errorEl = document.createElement("p");
        errorEl.setAttribute("data-validation-error", "true");
        errorEl.className = "input-error mt-1";
        input.insertAdjacentElement("afterend", errorEl);
    }
    errorEl.textContent = message;
}

function clearFieldError(input, showSuccess = true) {
    input.classList.remove(CSS_ERROR);
    if (showSuccess && input.value && input.value.trim() !== "") {
        input.classList.add(CSS_SUCCESS);
    } else {
        input.classList.remove(CSS_SUCCESS);
    }

    const errorEl = getErrorEl(input);
    if (errorEl) {
        errorEl.remove();
    }
}

// ── Field validation dispatch ─────────────────────────────────────────────────

function validateField(input) {
    const validator  = input.dataset.validator;
    const required   = input.dataset.required === "true";
    const min        = parseInt(input.dataset.min, 10)  || undefined;
    const max        = parseInt(input.dataset.max, 10)  || undefined;
    const optional   = input.dataset.phoneOptional === "true";
    const value      = input.value;

    let result = { valid: true, message: "" };

    switch (validator) {
        case "required":
            result = validateRequired(value);
            break;

        case "email":
            result = validateEmail(value);
            break;

        case "phone":
            result = validatePhone(value, !optional);
            break;

        case "name":
            if (!required && (!value || value.trim() === "")) {
                result = { valid: true, message: "" };
            } else {
                result = validateName(value, min || 2, max || 50);
            }
            break;

        case "name-long":
            if (!required && (!value || value.trim() === "")) {
                result = { valid: true, message: "" };
            } else {
                result = validateName(value, min || 2, max || 100);
            }
            break;

        case "rfid":
            result = validateRFID(value);
            break;

        case "roll-no":
            result = validateRollNo(value);
            break;

        case "text-length":
            result = validateLength(value, required, min || 0, max || 500);
            break;

        case "password":
            result = validatePassword(value, required);
            break;

        case "password-confirm": {
            const matchId  = input.dataset.matchField;
            const matchEl  = matchId ? document.getElementById(matchId) : null;
            const primary  = matchEl ? matchEl.value : "";
            const isRequired = required || (primary && primary !== "");
            result = validatePasswordMatch(primary, value, isRequired);
            break;
        }

        default:
            break;
    }

    if (result.valid) {
        clearFieldError(input);
    } else {
        showFieldError(input, result.message);
    }

    return result.valid;
}

// ── Form-level validation (called on submit) ──────────────────────────────────

function validateForm(formEl) {
    const inputs = formEl.querySelectorAll("[data-validator]");
    let allValid = true;

    inputs.forEach(function (input) {
        const fieldValid = validateField(input);
        if (!fieldValid) {
            allValid = false;
        }
    });

    return allValid;
}

// ── Attach handlers to a single form ─────────────────────────────────────────

function attachFormHandlers(formEl) {
    // Blur: validate individual field
    const inputs = formEl.querySelectorAll("[data-validator]");
    inputs.forEach(function (input) {
        input.addEventListener("blur", function () {
            validateField(input);
        });
    });

    // Submit: validate all fields, block if invalid
    formEl.addEventListener("submit", function (event) {
        const valid = validateForm(formEl);
        if (!valid) {
            event.preventDefault();
            // Scroll to first error
            const firstError = formEl.querySelector("." + CSS_ERROR);
            if (firstError) {
                firstError.scrollIntoView({ behavior: "smooth", block: "center" });
                firstError.focus();
            }
        }
    });
}

// ── Initialise: find all forms with at least one [data-validator] input ───────

function initFormValidation() {
    const forms = document.querySelectorAll("form");
    forms.forEach(function (formEl) {
        if (formEl.querySelector("[data-validator]")) {
            attachFormHandlers(formEl);
        }
    });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", initFormValidation);
document.addEventListener("htmx:afterSwap", initFormValidation);
