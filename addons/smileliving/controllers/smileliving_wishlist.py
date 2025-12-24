import logging
import re

from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class SmileLivingWishlist(WebsiteSaleWishlist):
    def _website_company(self):
        return request.website.company_id

    def _remove_wish_id_from_session(self, wish_id: int) -> None:
        if not request.website.is_public_user():
            return
        wish_ids = request.session.get('wishlist_ids') or []
        if wish_id in wish_ids:
            wish_ids.remove(wish_id)
            request.session['wishlist_ids'] = wish_ids
            request.session.touch()

    def _map_template_to_company(self, template, company):
        if not template or not company:
            return False

        if template.company_id and template.company_id.id == company.id:
            return template

        vn_code = None
        if getattr(template, 'default_code', None):
            vn_code = f"{template.default_code}-VN" if not template.default_code.endswith('-VN') else template.default_code
        if vn_code:
            mapped = request.env['product.template'].sudo().with_company(company).search([
                ('default_code', '=', vn_code),
                ('company_id', '=', company.id),
            ], limit=1)
            if mapped:
                return mapped

        base_name = (template.name or '').strip()
        base_name = re.sub(r"\s*\([^)]*\)\s*$", "", base_name).strip()
        if base_name:
            mapped = request.env['product.template'].sudo().with_company(company).search([
                ('name', 'ilike', base_name),
                ('company_id', '=', company.id),
            ], limit=1)
            if mapped:
                return mapped

        return False

    def _map_variant_to_website_company(self, variant):
        company = self._website_company()
        if not variant or not company:
            return False

        variant = variant.exists()
        if not variant:
            return False

        template = variant.product_tmpl_id

        # If already in website company, keep it.
        if template.company_id and template.company_id.id == company.id:
            return variant

        # SmileLiving wishlist only supports real-estate products.
        if not getattr(template, 'is_house', False):
            return False

        # Prefer mapping via internal reference (-VN).
        base_code = variant.default_code or getattr(template, 'default_code', None)
        if base_code:
            vn_code = base_code if base_code.endswith('-VN') else f"{base_code}-VN"

            mapped_variant = request.env['product.product'].sudo().with_company(company).search([
                ('default_code', '=', vn_code),
            ], limit=1)
            if mapped_variant and mapped_variant.product_tmpl_id.company_id and mapped_variant.product_tmpl_id.company_id.id == company.id:
                return mapped_variant

            mapped_template = request.env['product.template'].sudo().with_company(company).search([
                ('default_code', '=', vn_code),
                ('company_id', '=', company.id),
            ], limit=1)
            if mapped_template:
                mapped_variant = request.env['product.product'].sudo().with_company(company).search([
                    ('product_tmpl_id', '=', mapped_template.id),
                ], limit=1)
                if mapped_variant:
                    return mapped_variant

        # Fallback: map template by name, then pick its primary variant.
        mapped_template = self._map_template_to_company(template, company)
        if mapped_template:
            mapped_variant = request.env['product.product'].sudo().with_company(company).search([
                ('product_tmpl_id', '=', mapped_template.id),
            ], limit=1)
            if mapped_variant:
                return mapped_variant

        return False

    @route('/shop/wishlist', type='http', auth='public', website=True, sitemap=False)
    def get_wishlist(self, **kw):
        website = request.website
        wishlist_sudo = request.env['product.wishlist'].sudo().with_context(display_default_code=False).current()

        seen_public_product_ids = set()
        for wish in wishlist_sudo:
            try:
                mapped = self._map_variant_to_website_company(wish.product_id.sudo())
                if not mapped:
                    self._remove_wish_id_from_session(wish.id)
                    wish.unlink()
                    continue

                # Deduplicate: partner wishlists are unique by (product_id, partner_id).
                if wish.partner_id:
                    dup = request.env['product.wishlist'].sudo().search([
                        ('id', '!=', wish.id),
                        ('partner_id', '=', wish.partner_id.id),
                        ('product_id', '=', mapped.id),
                    ], limit=1)
                    if dup:
                        self._remove_wish_id_from_session(wish.id)
                        wish.unlink()
                        continue
                else:
                    # Public/session wishlist: keep only 1 per product.
                    if mapped.id in seen_public_product_ids:
                        self._remove_wish_id_from_session(wish.id)
                        wish.unlink()
                        continue
                    seen_public_product_ids.add(mapped.id)

                if wish.product_id.id != mapped.id:
                    wish.write({'product_id': mapped.id, 'website_id': website.id})

            except Exception:
                _logger.exception('Wishlist normalization failed for wish_id=%s', wish.id)

        wishes = request.env['product.wishlist'].with_context(display_default_code=False).current()
        return request.render('website_sale_wishlist.product_wishlist', {'wishes': wishes})

    @route('/shop/wishlist/get_product_ids', type='jsonrpc', auth='public', website=True, readonly=True)
    def shop_wishlist_get_product_ids(self):
        wishlist_sudo = request.env['product.wishlist'].sudo().current()
        product_ids = []
        for wish in wishlist_sudo:
            mapped = self._map_variant_to_website_company(wish.product_id.sudo())
            if mapped:
                product_ids.append(mapped.id)
        return product_ids

    @route('/shop/wishlist/add', type='jsonrpc', auth='public', website=True)
    def add_to_wishlist(self, product_id, **kw):
        # Normalize incoming product_id (old company) -> VN company
        variant = request.env['product.product'].sudo().browse(int(product_id)).exists()
        mapped = self._map_variant_to_website_company(variant) if variant else False
        if mapped:
            product_id = mapped.id
        return super().add_to_wishlist(product_id, **kw)
