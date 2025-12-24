/** @odoo-module **/

function replaceAddToCartWithInterest() {
    if (window.location.pathname !== '/shop/wishlist') {
        return;
    }

    const buttons = document.querySelectorAll(
        'button.o_wsale_product_btn_primary, a.o_wsale_product_btn_primary'
    );

    buttons.forEach((btn) => {
        if (btn.dataset.smilelivingInterestApplied === '1') {
            return;
        }

        const form = btn.closest('form');
        const tmplInput = form ? form.querySelector('input[name="product_template_id"]') : null;
        const templateId = tmplInput ? parseInt(tmplInput.value, 10) : NaN;
        if (!templateId) {
            return;
        }

        const interestUrl = `/smileliving/interest/${templateId}`;

        const interestEl = document.createElement('a');
        interestEl.dataset.smilelivingInterestApplied = '1';
        interestEl.href = interestUrl;
        interestEl.role = 'button';
        interestEl.title = 'Interest';
        interestEl.setAttribute('aria-label', 'Interest');
        interestEl.className = (btn.className || '')
            .split(/\s+/)
            .filter((c) => c && c !== 'a-submit')
            .join(' ');
        interestEl.textContent = 'Interest';

        btn.replaceWith(interestEl);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    replaceAddToCartWithInterest();
    const target = document.querySelector('main');
    if (target) {
        const mo = new MutationObserver(() => replaceAddToCartWithInterest());
        mo.observe(target, { childList: true, subtree: true });
    }
});

export { replaceAddToCartWithInterest };
