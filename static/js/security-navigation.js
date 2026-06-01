document.addEventListener('DOMContentLoaded', () => {
    const internalPrefixes = [
        '/dashboard/',
        '/clientes/',
        '/fornecedores/',
        '/produtos/',
        '/estoque/',
        '/vendas/',
        '/orcamentos/',
        '/fiscal/',
    ];

    function isInternalLink(link) {
        if (!link.href || link.classList.contains('allow-popup')) {
            return false;
        }

        const url = new URL(link.href, window.location.origin);
        if (url.origin !== window.location.origin) {
            return false;
        }

        return internalPrefixes.some((prefix) => url.pathname.startsWith(prefix));
    }

    document.querySelectorAll('a[href]').forEach((link) => {
        if (!isInternalLink(link)) {
            return;
        }

        link.addEventListener('contextmenu', (event) => {
            event.preventDefault();
        });

        link.addEventListener('mousedown', (event) => {
            if (event.button === 1) {
                event.preventDefault();
            }
        });

        link.addEventListener('auxclick', (event) => {
            if (event.button === 1) {
                event.preventDefault();
            }
        });

        link.addEventListener('click', (event) => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.button === 1) {
                event.preventDefault();
                window.location.assign(link.href);
            }
        });
    });
});
