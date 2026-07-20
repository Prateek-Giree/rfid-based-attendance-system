/**
 * sidebar.js — SAMS Mobile Responsive Sidebar Controller
 *
 * Responsibilities:
 *  - Open, close, and toggle the mobile sidebar drawer.
 *  - Handle backdrop visibility and click-to-close.
 *  - Close sidebar when the ESC key is pressed.
 *  - Close sidebar when a navigation link is clicked.
 *  - Re-initialize bindings after HTMX swaps.
 */

(function () {
    let sidebarEl = null;
    let backdropEl = null;

    function getElements() {
        sidebarEl = document.getElementById('app-sidebar');
        backdropEl = document.getElementById('sidebar-backdrop');
    }

    function isSidebarOpen() {
        if (!sidebarEl) return false;
        // The sidebar is considered open if it lacks the -translate-x-full class
        return !sidebarEl.classList.contains('-translate-x-full');
    }

    function openSidebar() {
        if (!sidebarEl || !backdropEl) return;
        
        // Slide in sidebar
        sidebarEl.classList.remove('-translate-x-full');
        
        // Show backdrop
        backdropEl.classList.remove('hidden');
        // Small delay to allow display:block to apply before animating opacity
        setTimeout(() => {
            backdropEl.classList.remove('opacity-0');
            backdropEl.classList.add('opacity-100');
        }, 10);
    }

    function closeSidebar() {
        if (!sidebarEl || !backdropEl) return;
        
        // Slide out sidebar
        sidebarEl.classList.add('-translate-x-full');
        
        // Hide backdrop
        backdropEl.classList.remove('opacity-100');
        backdropEl.classList.add('opacity-0');
        
        // Wait for transition to finish before hiding
        setTimeout(() => {
            if (!isSidebarOpen()) {
                backdropEl.classList.add('hidden');
            }
        }, 300); // Matches Tailwind's duration-300
    }

    function toggleSidebar() {
        if (isSidebarOpen()) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    // Expose to window for inline onclick handler (menu button)
    window.toggleSidebar = toggleSidebar;

    function initSidebar() {
        getElements();

        if (!sidebarEl || !backdropEl) return;

        // Backdrop click to close
        backdropEl.addEventListener('click', closeSidebar);

        // Escape key to close
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isSidebarOpen()) {
                closeSidebar();
            }
        });

        // Close when a link inside the sidebar is clicked
        const sidebarLinks = sidebarEl.querySelectorAll('a');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', () => {
                // Only close if it's on mobile (lg breakpoint is 1024px)
                if (window.innerWidth < 1024) {
                    closeSidebar();
                }
            });
        });
    }

    // Initialize on first load
    document.addEventListener('DOMContentLoaded', initSidebar);

    // Re-initialize after HTMX swaps to ensure event listeners are bound
    document.addEventListener('htmx:afterSwap', function () {
        // Only re-init if the sidebar itself was swapped, but safe to just run it
        initSidebar();
    });

})();
