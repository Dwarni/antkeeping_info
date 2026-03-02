(function () {
    const STORAGE_KEY = 'colorTheme';

    /** Return the resolved theme ('light' or 'dark') from a stored preference. */
    function resolveTheme(stored) {
        if (stored === 'dark' || stored === 'light') return stored;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    /** Apply the resolved theme to <html> and update all toggle button icons. */
    function applyTheme(resolved) {
        document.documentElement.setAttribute('data-bs-theme', resolved);
        updateButtons();
    }

    /** Cycle stored preference: auto -> dark -> light -> auto */
    function cyclePreference() {
        let stored;
        try { stored = localStorage.getItem(STORAGE_KEY) || 'auto'; } catch(e) { stored = 'auto'; }

        const next = stored === 'auto' ? 'dark' : stored === 'dark' ? 'light' : 'auto';
        try { localStorage.setItem(STORAGE_KEY, next); } catch(e) {}

        applyTheme(resolveTheme(next === 'auto' ? null : next));
    }

    /**
     * Update all .theme-toggle button icons and labels.
     *
     * Stored preference -> icon / label:
     *   'auto'  -> bi-circle-half  / "Switch to dark mode"
     *   'dark'  -> bi-moon-stars   / "Switch to light mode"
     *   'light' -> bi-sun          / "Switch to auto mode"
     */
    function updateButtons() {
        let stored;
        try { stored = localStorage.getItem(STORAGE_KEY) || 'auto'; } catch(e) { stored = 'auto'; }

        let iconClass, label;
        if (stored === 'dark') {
            iconClass = 'bi-moon-stars';
            label = 'Current: Dark mode – click for Light';
        } else if (stored === 'light') {
            iconClass = 'bi-sun';
            label = 'Current: Light mode – click for Auto';
        } else {
            iconClass = 'bi-circle-half';
            label = 'Current: Auto mode – click for Dark';
        }

        document.querySelectorAll('.theme-toggle').forEach(function(btn) {
            const icon = btn.querySelector('i');
            if (icon) { icon.className = 'bi ' + iconClass; }
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);
        });
    }

    /** Listen for OS preference changes when the user is in auto mode. */
    function watchOsPreference() {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            let stored;
            try { stored = localStorage.getItem(STORAGE_KEY) || 'auto'; } catch(e) { stored = 'auto'; }
            if (stored === 'auto' || stored === null) {
                applyTheme(resolveTheme(null));
            }
        });
    }

    function init() {
        updateButtons();
        document.querySelectorAll('.theme-toggle').forEach(function(btn) {
            btn.addEventListener('click', cyclePreference);
        });
        watchOsPreference();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
