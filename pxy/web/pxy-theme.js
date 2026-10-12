(() => {
    const root = document.documentElement;
    const paperTheme = root.dataset.paperTheme || 'light';
    function updateThemeColor(mode) {
        const themeColor = document.querySelector('meta[name="theme-color"]');
        if (themeColor) {
            themeColor.content = mode === 'dark' ? '#181c26' : '#f1ece2';
        }
    }

    function setTheme(mode) {
        root.dataset.theme = mode === 'dark' ? 'dark' : paperTheme;
        updateThemeColor(mode);
        root.dispatchEvent(new Event('pxy-theme-change'));
    }

    function saveTheme() {
        const mode = root.dataset.theme === 'dark' ? 'dark' : 'paper';
        try {
            if (localStorage.getItem('pxyTheme') !== mode) {
                localStorage.setItem('pxyTheme', mode);
            }
        } catch (error) {
            return;
        }
    }

    try {
        setTheme(localStorage.getItem('pxyTheme') === 'dark' ? 'dark' : 'paper');
    } catch (error) {
        setTheme('paper');
    }
    document.addEventListener('DOMContentLoaded', () => {
        updateThemeColor(root.dataset.theme === 'dark' ? 'dark' : 'paper');
    }, { once: true });

    new MutationObserver(saveTheme).observe(root, {
        attributes: true,
        attributeFilter: ['data-theme']
    });

    window.addEventListener('storage', (event) => {
        if (event.key === 'pxyTheme') {
            setTheme(event.newValue === 'dark' ? 'dark' : 'paper');
        }
    });
})();
