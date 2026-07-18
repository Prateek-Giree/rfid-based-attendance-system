/**
 * app.js — SAMS global JavaScript
 *
 * Responsibilities:
 *  1. Dark mode: read/write localStorage, toggle on <html>
 *  2. HTMX: global CSRF token injection + Lucide re-init after swaps
 *  3. Lucide: initialise icons on first load
 */

// ── 1. Dark Mode ─────────────────────────────────────────────────────────────

const THEME_KEY = "sams_theme";

function applyTheme(theme) {
    if (theme === "dark") {
        document.documentElement.classList.add("dark");
    } else {
        document.documentElement.classList.remove("dark");
    }
    // Update the toggle button icon if it exists
    updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const moonIcon = btn.querySelector("[data-lucide='moon']");
    const sunIcon  = btn.querySelector("[data-lucide='sun']");
    if (theme === "dark") {
        if (moonIcon) moonIcon.style.display = "none";
        if (sunIcon)  sunIcon.style.display  = "block";
    } else {
        if (moonIcon) moonIcon.style.display = "block";
        if (sunIcon)  sunIcon.style.display  = "none";
    }
}

function toggleTheme() {
    const current = localStorage.getItem(THEME_KEY) || "light";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
}

// Apply saved theme on every page load (DOMContentLoaded fires after inline script)
document.addEventListener("DOMContentLoaded", function () {
    const saved = localStorage.getItem(THEME_KEY) || "light";
    applyTheme(saved);

    const btn = document.getElementById("theme-toggle");
    if (btn) {
        btn.addEventListener("click", toggleTheme);
    }
});


// ── 2. HTMX — Global CSRF injection ──────────────────────────────────────────

document.addEventListener("htmx:configRequest", function (event) {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        event.detail.headers["X-CSRFToken"] = csrfMeta.content;
    }
});

// Re-initialise Lucide icons after every HTMX partial swap
document.addEventListener("htmx:afterSwap", function () {
    if (typeof lucide !== "undefined") {
        lucide.createIcons();
    }
});

// Re-initialise Lucide icons after HTMX out-of-band swap
document.addEventListener("htmx:oobAfterSwap", function () {
    if (typeof lucide !== "undefined") {
        lucide.createIcons();
    }
});


// ── 3. Lucide — initialise on first load ─────────────────────────────────────

document.addEventListener("DOMContentLoaded", function () {
    if (typeof lucide !== "undefined") {
        lucide.createIcons();
    }
});


// ── 4. SweetAlert2 — Delete confirmation helper ───────────────────────────────
// Usage in templates:
//   <button onclick="confirmDelete('{% url "..." %}')">Delete</button>

function confirmDelete(actionUrl, itemName) {
    Swal.fire({
        title: "Confirm Deletion",
        text: itemName
            ? `Are you sure you want to delete "${itemName}"? This action cannot be undone.`
            : "This action cannot be undone.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#EF4444",
        cancelButtonColor: "#64748B",
    }).then(function (result) {
        if (result.isConfirmed) {
            // Submit a hidden form to the action URL using POST
            const form = document.createElement("form");
            form.method = "POST";
            form.action = actionUrl;
            const csrf = document.querySelector('meta[name="csrf-token"]').content;
            const csrfInput = document.createElement("input");
            csrfInput.type = "hidden";
            csrfInput.name = "csrfmiddlewaretoken";
            csrfInput.value = csrf;
            form.appendChild(csrfInput);
            document.body.appendChild(form);
            form.submit();
        }
    });
}
