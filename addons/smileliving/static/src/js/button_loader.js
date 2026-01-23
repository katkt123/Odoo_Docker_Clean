/** @odoo-module */

// Simple client-side spinner for header action buttons
// Targets buttons by their `name` attribute used in the form header.

document.addEventListener('DOMContentLoaded', function () {
    function attach() {
        const selectors = [
            'button[name="action_submit"]',
            'button[name="action_approve_and_convert"]',
            'button[name="action_open_reject_wizard"]'
        ].join(',');
        document.querySelectorAll(selectors).forEach(btn => {
            // avoid double-binding
            if (btn.dataset.smileLoaderAttached) return;
            btn.dataset.smileLoaderAttached = '1';
            btn.addEventListener('click', function (ev) {
                // if button already disabled/read-only, do nothing
                if (btn.classList.contains('o_disabled') || btn.hasAttribute('disabled')) {
                    ev.preventDefault();
                    return;
                }
                // show spinner and disable visually
                btn.classList.add('o_smile_loading');
                btn.setAttribute('disabled', 'disabled');
                // preserve text
                btn.dataset._smile_orig = btn.innerHTML;
                // prepend spinner
                btn.innerHTML = '<span class="o_smile_spinner" aria-hidden="true"></span> ' + btn.innerHTML;
                // Leave the rest to the RPC/reload; we don't try to intercept response here
            });
        });
    }

    // attach initially and also after DOM changes (simple MutationObserver)
    attach();

    const observer = new MutationObserver(function (mutations) {
        attach();
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
