import json

from odoo import http
from odoo.http import request
from odoo.tools import remove_accents


class SmileLivingLivechatProduct(http.Controller):
    @http.route("/smileliving/livechat/search_product", type="json", auth="public", website=True, csrf=False)
    def search_product(self, term="", limit=5):
        website = request.website
        company = website.company_id
        Product = request.env["product.template"].sudo().with_company(company)

        domain = [
            ("sale_ok", "=", True),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company.id),
        ]
        # Always require published on website
        if "is_published" in Product._fields:
            domain.append(("is_published", "=", True))
        elif "website_published" in Product._fields:
            domain.append(("website_published", "=", True))
        if term:
            domain += ["|", ("name", "ilike", term), ("default_code", "ilike", term)]

        # Fetch a broader set to allow Python-side accent-insensitive filtering.
        products = Product.search(domain, limit=int(limit) * 4)

        term_norm = remove_accents(term or "").lower()

        def _match(prod):
            if not term_norm:
                return True
            name_norm = remove_accents(prod.name or "").lower()
            code_norm = remove_accents((prod.default_code or "")).lower()
            return term_norm in name_norm or term_norm in code_norm

        filtered = [p for p in products if _match(p)] or products
        products = filtered[: int(limit)]
        pricelist = None
        if hasattr(website, "_get_and_cache_current_pricelist"):
            pricelist = website._get_and_cache_current_pricelist()

        def _price_for(product):
            if pricelist:
                # Prefer variant if exists
                variant = product.product_variant_id or product
                return pricelist._get_product_price(variant, 1.0)
            return product.list_price

        res = []
        for product in products:
            price = _price_for(product)
            currency = pricelist.currency_id if pricelist else (product.currency_id or company.currency_id)
            price_display = f"{price:,.0f} {currency.symbol or ''}".strip()
            res.append(
                {
                    "id": product.id,
                    "variant_id": product.product_variant_id.id,
                    "name": product.name,
                    "url": product.website_url or "/shop",
                    "price": price,
                    "price_display": price_display,
                    "image_url": f"/web/image/product.template/{product.id}/image_512",
                }
            )
        return res


class SmileLivingLivechatProductInfo(http.Controller):
    @http.route("/smileliving/livechat/product_info", type="json", auth="public", website=True, csrf=False)
    def product_info(self, product_id=None):
        """Return product payload for livechat card rendering.

        We scope to the current website company and require the product to be saleable
        and published on the website.
        """
        website = request.website
        company = website.company_id
        # Accept both flat JSON ({"product_id": 123}) and JSON-RPC style ({"params": {"product_id": 123}}).
        parsed_body = {}
        try:
            raw = request.httprequest.get_data(as_text=True)
            if raw:
                parsed_body = json.loads(raw)
        except Exception:
            parsed_body = {}

        if product_id is None:
            params_body = request.params or {}
            product_id = (
                parsed_body.get("product_id")
                or parsed_body.get("params", {}).get("product_id")
                or params_body.get("product_id")
                or params_body.get("params", {}).get("product_id")
            )
        if not product_id:
            return {
                "id": False,
                "variant_id": False,
                "name": "Sản phẩm không xác định",
                "url": "/shop",
                "price": 0.0,
                "price_display": "Không khả dụng",
                "image_url": "/web/static/img/placeholder.png",
                "unavailable": True,
            }

        try:
            pid_int = int(product_id)
        except Exception:
            pid_int = False

        allowed_companies = request.env.companies.ids or [company.id]
        Product = request.env["product.template"].sudo().with_context(allowed_company_ids=allowed_companies)
        product = Product.browse(pid_int).exists() if pid_int else Product.browse()
        if not product or not product.sale_ok:
            return {
                "id": pid_int or product_id,
                "variant_id": False,
                "name": f"Sản phẩm #{product_id}",
                "url": "/shop",
                "price": 0.0,
                "price_display": "Không khả dụng",
                "image_url": "/web/static/img/placeholder.png",
                "unavailable": True,
            }
        # Loosen company/publication constraints so old messages still render even if product was unpublished or moved.
        # We still filter price by current website/company.
        if product.company_id and product.company_id != company:
            product = product.with_company(company)

        pricelist = None
        if hasattr(website, "_get_and_cache_current_pricelist"):
            pricelist = website._get_and_cache_current_pricelist()

        if pricelist:
            variant = product.product_variant_id or product
            price = pricelist._get_product_price(variant, 1.0)
            currency = pricelist.currency_id
        else:
            price = product.list_price
            currency = product.currency_id or company.currency_id

        price_display = f"{price:,.0f} {currency.symbol or ''}".strip()
        return {
            "id": product.id,
            "variant_id": product.product_variant_id.id,
            "name": product.name,
            "url": product.website_url or "/shop",
            "price": price,
            "price_display": price_display,
            "image_url": f"/web/image/product.template/{product.id}/image_512",
            "unavailable": False,
        }


class SmileLivingLivechatCart(http.Controller):
    @http.route("/smileliving/livechat/add_to_cart", type="json", auth="public", website=True, csrf=False)
    def add_to_cart(self, product_id=None, quantity=1):
        website = request.website
        company = website.company_id
        if not product_id:
            return {"error": "missing_product"}

        try:
            qty = float(quantity or 1.0)
        except Exception:
            qty = 1.0

        Product = request.env["product.product"].sudo().with_company(company)
        product = Product.browse(int(product_id)).exists()
        if not product or not product.sale_ok:
            return {"error": "unavailable"}

        tmpl = product.product_tmpl_id
        if tmpl.company_id and tmpl.company_id != company:
            return {"error": "wrong_company"}
        if "is_published" in tmpl._fields and not tmpl.is_published:
            return {"error": "unpublished"}
        if "website_published" in tmpl._fields and not tmpl.website_published:
            return {"error": "unpublished"}

        order = website.sale_get_order(force_create=True)
        if not order:
            return {"error": "no_order"}

        order = order.with_company(company)
        order._cart_update(product_id=product.id, add_qty=qty)

        return {"result": {"order_id": order.id, "cart_qty": order.cart_quantity}}
