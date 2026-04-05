(function () {
    const sidebarToggle = document.getElementById('sidebar-toggle-anchor');
    const html = document.documentElement;
    const storageKey = 'python-tutorial-sidebar';

    function applySidebarState(checked) {
        if (checked) {
            html.classList.add('sidebar-visible');
        } else {
            html.classList.remove('sidebar-visible');
        }
        try {
            localStorage.setItem(storageKey, checked ? 'visible' : 'hidden');
        } catch (err) {
            /* localStorage might be unavailable, ignore */
        }
    }

    if (sidebarToggle) {
        let stored = null;
        try {
            stored = localStorage.getItem(storageKey);
        } catch (err) {
            stored = null;
        }
        if (stored === 'hidden') {
            sidebarToggle.checked = false;
        }
        applySidebarState(sidebarToggle.checked);
        sidebarToggle.addEventListener('change', function () {
            applySidebarState(sidebarToggle.checked);
        });
        html.classList.add('js');
    }

    const currentLink = document.querySelector('.sidebar a[data-current="true"]');
    if (currentLink) {
        currentLink.setAttribute('aria-current', 'page');
        const scrollbox = document.querySelector('.sidebar-scrollbox');
        if (scrollbox) {
            const offset = currentLink.offsetTop - scrollbox.clientHeight * 0.3;
            scrollbox.scrollTop = Math.max(offset, 0);
        }
    }
})();

(function () {
    const themeToggle = document.getElementById('theme-toggle');
    const themeList = document.getElementById('theme-list');
    if (!themeToggle || !themeList) {
        return;
    }

    const html = document.documentElement;
    const storageKey = window.theme_storage_key || 'mdbook-theme';
    const defaultLight = window.default_light_theme || 'light';
    const defaultDark = window.default_dark_theme || 'navy';
    const metaTag = document.querySelector('meta[name="theme-color"]');
    const highlightLinks = {
        base: document.getElementById('highlight-css'),
        tomorrow: document.getElementById('tomorrow-night-css'),
        ayu: document.getElementById('ayu-highlight-css'),
    };

    const buttons = Array.from(themeList.querySelectorAll('button.theme'));
    const actualThemes = buttons
        .map(function (btn) { return btn.id; })
        .filter(function (id) { return id !== 'default_theme'; });
    const allIds = buttons.map(function (btn) { return btn.id; });

    function prefersDark() {
        return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    }

    function savedSelection() {
        try {
            return localStorage.getItem(storageKey);
        } catch (err) {
            return null;
        }
    }

    function saveSelection(selection) {
        try {
            localStorage.setItem(storageKey, selection);
        } catch (err) {
            /* ignore */
        }
    }

    function clearSelection() {
        try {
            localStorage.removeItem(storageKey);
        } catch (err) {
            /* ignore */
        }
    }

    function resolveTheme(selection) {
        if (!selection || selection === 'default_theme') {
            return prefersDark() ? defaultDark : defaultLight;
        }
        if (!actualThemes.includes(selection)) {
            return defaultLight;
        }
        return selection;
    }

    function updateHighlight(theme) {
        if (highlightLinks.ayu) {
            highlightLinks.ayu.disabled = theme !== 'ayu';
        }
        if (highlightLinks.tomorrow) {
            highlightLinks.tomorrow.disabled = !(theme === 'coal' || theme === 'navy');
        }
        if (highlightLinks.base) {
            highlightLinks.base.disabled = (theme === 'coal' || theme === 'navy' || theme === 'ayu');
        }
    }

    function updateMetaTheme() {
        if (!metaTag) {
            return;
        }
        window.setTimeout(function () {
            metaTag.content = getComputedStyle(document.documentElement).backgroundColor;
        }, 1);
    }

    function updateSelected(selection) {
        buttons.forEach(function (btn) {
            const selected = selection === 'default_theme'
                ? btn.id === 'default_theme'
                : btn.id === selection;
            btn.classList.toggle('theme-selected', selected);
        });
    }

    function removeThemeClasses() {
        actualThemes.forEach(function (theme) {
            html.classList.remove(theme);
        });
    }

    function applyTheme(selection, store) {
        const resolved = resolveTheme(selection);
        removeThemeClasses();
        html.classList.add(resolved);
        updateHighlight(resolved);
        updateMetaTheme();
        if (store) {
            if (selection === 'default_theme') {
                clearSelection();
            } else {
                saveSelection(selection);
            }
        }
        currentSelection = selection;
        window.default_theme = resolved;
        updateSelected(selection);
    }

    let currentSelection = savedSelection();
    if (!currentSelection) {
        currentSelection = 'default_theme';
    } else if (!allIds.includes(currentSelection)) {
        if (!actualThemes.includes(currentSelection)) {
            currentSelection = 'default_theme';
        }
    }
    updateSelected(currentSelection);
    applyTheme(currentSelection, false);

    function openPopup() {
        updateSelected(currentSelection);
        themeList.style.display = 'block';
        themeToggle.setAttribute('aria-expanded', 'true');
        const selectedButton = themeList.querySelector('.theme-selected');
        const target = selectedButton || themeList.querySelector('button.theme');
        if (target) {
            target.focus();
        }
        document.addEventListener('click', handleDocumentClick, true);
        document.addEventListener('keydown', handleKeydown);
    }

    function closePopup() {
        themeList.style.display = 'none';
        themeToggle.setAttribute('aria-expanded', 'false');
        document.removeEventListener('click', handleDocumentClick, true);
        document.removeEventListener('keydown', handleKeydown);
    }

    function handleDocumentClick(event) {
        if (themeList.contains(event.target) || themeToggle.contains(event.target)) {
            return;
        }
        closePopup();
    }

    function handleKeydown(event) {
        if (event.key === 'Escape') {
            if (themeList.style.display === 'block') {
                event.preventDefault();
                closePopup();
                themeToggle.focus();
            }
            return;
        }

        if (!themeList.contains(document.activeElement)) {
            return;
        }

        const activeButton = document.activeElement && document.activeElement.closest('button.theme');
        if (!activeButton) {
            return;
        }

        const index = buttons.indexOf(activeButton);
        if (index === -1) {
            return;
        }

        let nextIndex = index;
        if (event.key === 'ArrowUp') {
            event.preventDefault();
            nextIndex = index <= 0 ? buttons.length - 1 : index - 1;
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            nextIndex = (index + 1) % buttons.length;
        } else if (event.key === 'Home') {
            event.preventDefault();
            nextIndex = 0;
        } else if (event.key === 'End') {
            event.preventDefault();
            nextIndex = buttons.length - 1;
        } else {
            return;
        }

        const target = buttons[nextIndex];
        if (target) {
            target.focus();
        }
    }

    themeList.style.display = 'none';

    themeToggle.addEventListener('click', function (event) {
        event.preventDefault();
        if (themeList.style.display === 'block') {
            closePopup();
        } else {
            openPopup();
        }
    });

    themeList.addEventListener('click', function (event) {
        const button = event.target.closest('button.theme');
        if (!button) {
            return;
        }
        const selection = button.id;
        applyTheme(selection, true);
        closePopup();
        themeToggle.focus();
    });

    const mediaQuery = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    if (mediaQuery) {
        const handler = function () {
            if (currentSelection === 'default_theme') {
                applyTheme('default_theme', false);
            }
        };
        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handler);
        } else if (typeof mediaQuery.addListener === 'function') {
            mediaQuery.addListener(handler);
        }
    }
})();

(function () {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js';
    script.onload = function () {
        document.querySelectorAll('pre.literal-block').forEach(function (pre) {
            const text = pre.textContent;
            const code = document.createElement('code');
            code.className = /^\s*>>>/.test(text) ? 'language-python-repl' : 'language-python';
            code.textContent = text;
            pre.textContent = '';
            pre.appendChild(code);
            hljs.highlightElement(code);
        });
    };
    document.head.appendChild(script);
})();
