import re

from odoo import http
from odoo.api import Environment as ApiEnvironment
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.fields import Domain

class SmileLivingShop(WebsiteSale):

    def _smileliving_get_property_product_ids(self, website_company):
        """Return (product_template_ids, has_filters, any_props_exist) based on request args."""
        request_args = request.httprequest.args

        def _first(val):
            return val[0] if isinstance(val, list) and val else val

        def _safe_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        def _safe_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        prop_domain = [
            ('company_id', 'in', [website_company.id, False]),
        ]

        has_smileliving_filters = False

        # Location filters
        tinhthanh_id = _safe_int(_first(request_args.get('tinhthanh_id', '')))
        quanhuyen_id = _safe_int(_first(request_args.get('quanhuyen_id', '')))
        phuongxa_id = _safe_int(_first(request_args.get('phuongxa_id', '')))
        if tinhthanh_id:
            prop_domain.append(('tinhthanh_id', '=', tinhthanh_id))
            has_smileliving_filters = True
        if quanhuyen_id:
            prop_domain.append(('quanhuyen_id', '=', quanhuyen_id))
            has_smileliving_filters = True
        if phuongxa_id:
            prop_domain.append(('phuongxa_id', '=', phuongxa_id))
            has_smileliving_filters = True

        # Property type (multi)
        filter_type_ids = []
        if hasattr(request_args, 'getlist'):
            filter_type_ids = [_safe_int(v) for v in request_args.getlist('filter_type_id')]
        else:
            filter_type_ids = [_safe_int(_first(request_args.get('filter_type_id', '')))]
        filter_type_ids = [v for v in filter_type_ids if v]
        if filter_type_ids:
            prop_domain.append(('type_id', 'in', tuple(filter_type_ids)))
            has_smileliving_filters = True

        # Amenities (multi)
        filter_amenity_ids = []
        if hasattr(request_args, 'getlist'):
            filter_amenity_ids = [_safe_int(v) for v in request_args.getlist('filter_amenity_id')]
        else:
            filter_amenity_ids = [_safe_int(_first(request_args.get('filter_amenity_id', '')))]
        filter_amenity_ids = [v for v in filter_amenity_ids if v]
        if filter_amenity_ids:
            prop_domain.append(('amenity_ids', 'in', tuple(filter_amenity_ids)))
            has_smileliving_filters = True

        # Sale type
        type_sale = _first(request_args.get('type_sale', ''))
        if type_sale in ('sale', 'rent'):
            prop_domain.append(('type_sale', '=', type_sale))
            has_smileliving_filters = True

        listing_source = _first(request_args.get('listing_source', ''))
        if listing_source == 'individual':
            prop_domain.append(('project_id', '=', False))
            has_smileliving_filters = True
        elif listing_source == 'broker':
            prop_domain.append(('project_id', '!=', False))
            has_smileliving_filters = True

        # Area range
        filter_area_min = _safe_float(_first(request_args.get('filter_area_min', '')))
        filter_area_max = _safe_float(_first(request_args.get('filter_area_max', '')))
        if filter_area_min is not None:
            prop_domain.append(('area', '>=', filter_area_min))
            has_smileliving_filters = True
        if filter_area_max is not None:
            prop_domain.append(('area', '<=', filter_area_max))
            has_smileliving_filters = True

        Property = request.env['smileliving.property'].sudo()
        any_props_exist = bool(Property.search_count([('company_id', 'in', [website_company.id, False])], limit=1))
        if not any_props_exist:
            return [], has_smileliving_filters, any_props_exist

        prop_recs = Property.search(prop_domain)
        product_ids = prop_recs.mapped('product_tmpl_id').ids
        return product_ids, has_smileliving_filters, any_props_exist

    def _is_shop_visible_template(self, product_tmpl):
        """Hard rule: never show archived/unpublished products, even to editors/admin."""
        ProductTmpl = request.env['product.template']
        if 'active' in ProductTmpl._fields and not bool(product_tmpl.active):
            return False
        if 'is_published' in ProductTmpl._fields and not bool(product_tmpl.is_published):
            return False
        if 'website_published' in ProductTmpl._fields and not bool(product_tmpl.website_published):
            return False
        return True

    def _website_company(self):
        return request.website.company_id

    def _map_template_to_company(self, template, company):
        if not template or not company:
            return False

        if template.company_id and template.company_id.id == company.id:
            return template
        

        # Prefer mapping via internal reference (-VN).
        vn_code = None
        if template.default_code:
            vn_code = f"{template.default_code}-VN" if not template.default_code.endswith('-VN') else template.default_code
        if vn_code:
            mapped = request.env['product.template'].sudo().with_company(company).search([
                ('default_code', '=', vn_code),
                ('company_id', '=', company.id),
            ], limit=1)
            if mapped:
                return mapped

        # Fallback: match base name (strip any trailing " (...)" suffix).
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

    def _shop_lookup_products(self, options, post, search, website):
        """Apply SmileLiving filters to the actual product lookup.

        In Odoo 19, the shop listing uses `website._search_with_fuzzy(...)` and does not
        consume `_get_products_domain` for the main result set. So we post-filter the
        returned recordset by the linked `smileliving.property` constraints.
        """
        fuzzy_search_term, product_count, search_product = super()._shop_lookup_products(
            options, post, search, website
        )

        website_company = self._website_company()
        property_product_ids, has_smileliving_filters, any_props_exist = self._smileliving_get_property_product_ids(
            website_company
        )

        if any_props_exist or has_smileliving_filters:
            allowed_ids = set(property_product_ids)
            ordered_ids = [pid for pid in search_product.ids if pid in allowed_ids]
            search_product = request.env['product.template'].browse(ordered_ids).with_context(bin_size=True)

        # Enforce strict hide rule (never show archived/unpublished products)
        ProductTmpl = request.env['product.template']
        visible_domain = Domain('id', 'in', search_product.ids)
        if 'active' in ProductTmpl._fields:
            visible_domain &= Domain('active', '=', True)
        if 'is_published' in ProductTmpl._fields:
            visible_domain &= Domain('is_published', '=', True)
        elif 'website_published' in ProductTmpl._fields:
            visible_domain &= Domain('website_published', '=', True)
        visible_ids = set(ProductTmpl.sudo().search(visible_domain).ids)
        if visible_ids:
            ordered_ids = [pid for pid in search_product.ids if pid in visible_ids]
            search_product = ProductTmpl.browse(ordered_ids).with_context(bin_size=True)
        else:
            search_product = ProductTmpl.browse([])

        return fuzzy_search_term, len(search_product), search_product

    def _try_redirect_or_render_product(self, product, category='', search='', **kwargs):
        website_company = self._website_company()
        product = self._map_template_to_company(product, website_company) or product
        product = request.env['product.template'].sudo().with_company(website_company).browse(product.id).exists()
        if not product:
            return request.not_found()

        if not self._is_shop_visible_template(product):
            return request.not_found()

        # Redirect to canonical URL if needed (covers mapping to -VN id too)
        canonical = product.website_url
        if canonical and request.httprequest.path != canonical:
            return request.redirect(canonical, code=302)

        return super().product(product, category=category, search=search, **kwargs)

    @http.route(['/shop/<model("product.template"):product>'], type='http', auth='public', website=True, sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        return self._try_redirect_or_render_product(product, category=category, search=search, **kwargs)

    # Fallback route for cases where the model converter triggers multi-company access errors
    # before reaching the controller (e.g., logged-in users with limited allowed companies).
    @http.route(['/shop/<string:slug>'], type='http', auth='public', website=True, sitemap=False)
    def product_slug_fallback(self, slug, **kwargs):
        match = re.search(r'-(\d+)$', slug or '')
        if not match:
            return request.not_found()

        template_id = int(match.group(1))
        template = request.env['product.template'].sudo().browse(template_id).exists()
        if not template:
            return request.not_found()

        return self._try_redirect_or_render_product(template, **kwargs)

    def _get_shop_domain(self, search_term, category, attribute_value_dict):
        """Override to apply SmileLiving filters on the /shop domain (Odoo 19 uses this hook)."""
        domain = super()._get_shop_domain(search_term, category, attribute_value_dict)

        # Always hide archived/unpublished products on /shop.
        # Odoo can show unpublished items (greyed out) to website editors/admins for preview.
        # User request: never show them at all.
        ProductTmpl = request.env['product.template']
        if 'active' in ProductTmpl._fields:
            domain &= Domain('active', '=', True)
        if 'is_published' in ProductTmpl._fields:
            domain &= Domain('is_published', '=', True)
        elif 'website_published' in ProductTmpl._fields:
            domain &= Domain('website_published', '=', True)

        website_company = self._website_company()
        product_ids, has_smileliving_filters, any_props_exist = self._smileliving_get_property_product_ids(website_company)

        # If there are no property records yet (fresh vertical-model rollout), don't blank /shop.
        if not any_props_exist and not has_smileliving_filters:
            return domain

        return domain & Domain('id', 'in', product_ids)

    def _shop_get_query_url_kwargs(self, search, min_price, max_price, **post):
        """Override để thêm các filter SmileLiving vào keep() function"""
        kwargs = super()._shop_get_query_url_kwargs(search, min_price, max_price, **post)
        
        # Lấy các filter parameters từ request
        request_args = request.httprequest.args

        # WebsiteSale thường set min_price/max_price theo available range -> dẫn tới URL luôn có
        # &min_price=...&max_price=... dù user chưa lọc. Chỉ giữ lại nếu user thực sự truyền.
        raw_min_price = request_args.get('min_price', '')
        raw_max_price = request_args.get('max_price', '')
        if not raw_min_price:
            kwargs.pop('min_price', None)
        if not raw_max_price:
            kwargs.pop('max_price', None)

        filter_type_id = request_args.getlist('filter_type_id') if hasattr(request_args, 'getlist') else request_args.get('filter_type_id', '')
        filter_amenity_id = request_args.getlist('filter_amenity_id') if hasattr(request_args, 'getlist') else request_args.get('filter_amenity_id', '')
        type_sale = request_args.get('type_sale', '')
        filter_area_min = request_args.get('filter_area_min', '')
        filter_area_max = request_args.get('filter_area_max', '')
        listing_source = request_args.get('listing_source', '')
        # (Removed) price filtering
        
        # Lấy filter địa lý
        tinhthanh_id = request_args.get('tinhthanh_id', '')
        quanhuyen_id = request_args.get('quanhuyen_id', '')
        phuongxa_id = request_args.get('phuongxa_id', '')
        
        # Xử lý nếu là list (multi select)
        if isinstance(filter_type_id, (list, tuple)):
            filter_type_id = [v for v in filter_type_id if v]
        if isinstance(filter_amenity_id, (list, tuple)):
            filter_amenity_id = [v for v in filter_amenity_id if v]
        if isinstance(type_sale, list):
            type_sale = type_sale[0] if type_sale else ''
        
        # Thêm vào kwargs để keep() giữ lại khi chuyển trang
        if filter_type_id:
            kwargs['filter_type_id'] = filter_type_id
        if filter_amenity_id:
            kwargs['filter_amenity_id'] = filter_amenity_id
        if type_sale:
            kwargs['type_sale'] = type_sale
        if filter_area_min:
            kwargs['filter_area_min'] = filter_area_min
        if filter_area_max:
            kwargs['filter_area_max'] = filter_area_max
        if listing_source:
            kwargs['listing_source'] = listing_source
        # (Removed) price filtering
        
        # Thêm filter địa lý vào kwargs
        if tinhthanh_id:
            kwargs['tinhthanh_id'] = tinhthanh_id
        if quanhuyen_id:
            kwargs['quanhuyen_id'] = quanhuyen_id
        if phuongxa_id:
            kwargs['phuongxa_id'] = phuongxa_id
        
        return kwargs

    def _get_search_domain(self, search, category, attrib_values):
        """Apply SmileLiving filtering on the search domain used for product lookup."""
        domain = super()._get_search_domain(search, category, attrib_values)

        ProductTmpl = request.env['product.template']
        if 'active' in ProductTmpl._fields:
            domain &= Domain('active', '=', True)
        if 'is_published' in ProductTmpl._fields:
            domain &= Domain('is_published', '=', True)
        elif 'website_published' in ProductTmpl._fields:
            domain &= Domain('website_published', '=', True)

        website_company = self._website_company()
        product_ids, has_smileliving_filters, any_props_exist = self._smileliving_get_property_product_ids(website_company)
        if not any_props_exist and not has_smileliving_filters:
            return domain
        return domain & Domain('id', 'in', product_ids)

    def _get_products_domain(self, search, category, attrib_values, **kwargs):
        """Apply SmileLiving filtering on the actual product listing domain."""
        domain = super()._get_products_domain(search, category, attrib_values, **kwargs)

        ProductTmpl = request.env['product.template']
        if 'active' in ProductTmpl._fields:
            domain &= Domain('active', '=', True)
        if 'is_published' in ProductTmpl._fields:
            domain &= Domain('is_published', '=', True)
        elif 'website_published' in ProductTmpl._fields:
            domain &= Domain('website_published', '=', True)

        website_company = self._website_company()
        product_ids, has_smileliving_filters, any_props_exist = self._smileliving_get_property_product_ids(website_company)
        if not any_props_exist and not has_smileliving_filters:
            return domain
        return domain & Domain('id', 'in', product_ids)

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth='public', website=True)
    def shop(self, page=0, category='', search='', **kwargs):
        """Override shop method để thêm context cho filter"""
        # Ensure multi-company context matches the current website.
        # Portal users may have a different allowed_company_ids, which would blank /shop.
        website_company = self._website_company()

        # Multi-company gotcha:
        # - Forcing allowed_company_ids to a company the current (portal) user is not allowed for
        #   raises: "Access to unauthorized or invalid companies."
        # - But we still want /shop to behave like a public page (visible products only).
        # Solution: if the current user isn't allowed for the website company, temporarily
        # render the shop page as the website public user scoped to the website company.
        response = None
        if website_company and website_company.id in request.env.user.company_ids.ids:
            request.update_context(allowed_company_ids=[website_company.id])
            response = super().shop(category=category, search=search, **kwargs)
        elif website_company and request.website and request.website.user_id:
            old_env = request.env
            try:
                # Use superuser to avoid multi-company validation errors for portal users.
                # We still keep the shop domains strict (published/active) in the other hooks.
                fallback_uid = 1
                new_context = dict(old_env.context)
                new_context.update({
                    'allowed_company_ids': [website_company.id],
                    'force_company': website_company.id,
                    'allowed_company_id': website_company.id,
                })
                request.env = ApiEnvironment(old_env.cr, fallback_uid, new_context)
                response = super().shop(category=category, search=search, **kwargs)
            finally:
                request.env = old_env
        else:
            response = super().shop(category=category, search=search, **kwargs)
        
        # Lấy filter parameters từ request.httprequest.args (đúng cách)
        # Vì kwargs có thể không có khi chuyển trang
        request_args = request.httprequest.args
        # Multi-select filters must use getlist() (otherwise only 1 value is kept)
        filter_type_id = request_args.getlist('filter_type_id') if hasattr(request_args, 'getlist') else (kwargs.get('filter_type_id', '') or '')
        filter_amenity_id = request_args.getlist('filter_amenity_id') if hasattr(request_args, 'getlist') else (kwargs.get('filter_amenity_id', '') or '')
        type_sale = request_args.get('type_sale', '') or kwargs.get('type_sale', '')
        filter_area_min = request_args.get('filter_area_min', '') or kwargs.get('filter_area_min', '')
        filter_area_max = request_args.get('filter_area_max', '') or kwargs.get('filter_area_max', '')
        listing_source = request_args.get('listing_source', '') or kwargs.get('listing_source', '')
        # (Removed) price filtering
        
        # Lấy filter địa lý
        tinhthanh_id = request_args.get('tinhthanh_id', '') or kwargs.get('tinhthanh_id', '')
        quanhuyen_id = request_args.get('quanhuyen_id', '') or kwargs.get('quanhuyen_id', '')
        phuongxa_id = request_args.get('phuongxa_id', '') or kwargs.get('phuongxa_id', '')
        
        # Normalize multi-select lists (drop empties)
        if isinstance(filter_type_id, (list, tuple)):
            filter_type_id = [v for v in filter_type_id if v]
        elif filter_type_id:
            filter_type_id = [filter_type_id]

        if isinstance(filter_amenity_id, (list, tuple)):
            filter_amenity_id = [v for v in filter_amenity_id if v]
        elif filter_amenity_id:
            filter_amenity_id = [filter_amenity_id]
        if isinstance(type_sale, list):
            type_sale = type_sale[0] if type_sale else ''

        # Available min/max area for slider.
        # Prefer computing from the currently displayed products to avoid mismatches
        # when website/company context and property ownership diverge.
        website_company = website_company or self._website_company()

        Property = request.env['smileliving.property'].sudo()
        products = response.qcontext.get('products')

        # NOTE: Odoo's read_group aggregates can be tricky to parse (keys may not be
        # `area_min/area_max` as expected). Use ordered searches for reliability.
        area_domain = [('area', '>', 0)]
        if products and getattr(products, 'ids', None):
            area_domain.append(('product_tmpl_id', 'in', products.ids))
        else:
            area_domain.append(('company_id', 'in', [website_company.id, False]))

        min_prop = Property.search(area_domain, order='area asc', limit=1)
        max_prop = Property.search(area_domain, order='area desc', limit=1)

        available_min_area = float(min_prop.area) if min_prop else 0.0
        available_max_area = float(max_prop.area) if max_prop else 0.0

        # User preference: always start the slider at 1 m².
        available_min_area = 1.0

        # Debug helpers (temporary; used to diagnose range issues on live pages)
        response.qcontext['smile_debug_db'] = request.db
        response.qcontext['smile_debug_website_id'] = request.website.id if request.website else False
        response.qcontext['smile_debug_website_company_id'] = website_company.id if website_company else False
        response.qcontext['smile_debug_products_ids'] = products.ids if products and getattr(products, 'ids', None) else []
        response.qcontext['smile_debug_area_domain'] = area_domain
        response.qcontext['smile_debug_area_min'] = available_min_area
        response.qcontext['smile_debug_area_max'] = available_max_area

        # Avoid a degenerate range (min == max) which makes the range slider not draggable.
        # This typically happens when there is no valid `area` data yet.
        if available_max_area <= available_min_area:
            available_max_area = available_min_area + 1.0

        def _safe_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        current_area_min = _safe_float(filter_area_min)
        current_area_max = _safe_float(filter_area_max)
        if current_area_min is None:
            current_area_min = available_min_area
        if current_area_max is None:
            current_area_max = available_max_area

        # Clamp current values into the available range.
        current_area_min = max(available_min_area, min(current_area_min, available_max_area))
        current_area_max = max(available_min_area, min(current_area_max, available_max_area))
        if current_area_max < current_area_min:
            current_area_min, current_area_max = current_area_max, current_area_min
        
        # Lấy danh sách property types để hiển thị trong filter
        property_types = request.env['smileliving.type'].sudo().search([
            ('active', '=', True)
        ])

        # Lấy danh sách tiện ích để hiển thị trong filter
        amenities = request.env['smileliving.amenity'].sudo().search([
            ('active', '=', True)
        ], order='name')
        
        # Lấy dữ liệu địa lý
        tinhthanhs = request.env['tinh.thanh'].sudo().search([
            ('active', '=', True)
        ], order='name')
        
        quanhuyens = request.env['quan.huyen'].sudo().search([
            ('active', '=', True)
        ], order='name')
        
        phuongxas = request.env['phuong.xa'].sudo().search([
            ('active', '=', True)
        ], order='name')
        
        # Cập nhật context với thông tin filter
        response.qcontext['property_types'] = property_types
        response.qcontext['amenities'] = amenities
        response.qcontext['tinhthanhs'] = tinhthanhs
        response.qcontext['quanhuyens'] = quanhuyens
        response.qcontext['phuongxas'] = phuongxas
        response.qcontext['filter_type_id'] = filter_type_id
        response.qcontext['filter_amenity_id'] = filter_amenity_id
        response.qcontext['type_sale'] = type_sale
        response.qcontext['filter_area_min'] = current_area_min
        response.qcontext['filter_area_max'] = current_area_max
        response.qcontext['available_min_area'] = available_min_area
        response.qcontext['available_max_area'] = available_max_area
        response.qcontext['listing_source'] = listing_source
        # (Removed) price filtering
        
        # Thêm context cho filter địa lý
        response.qcontext['tinhthanh_id'] = tinhthanh_id
        response.qcontext['quanhuyen_id'] = quanhuyen_id
        response.qcontext['phuongxa_id'] = phuongxa_id

        # Provide property records for product cards (avoid N+1 queries in QWeb)
        products = response.qcontext.get('products')
        properties_by_template_id = {}
        if products and getattr(products, 'ids', None):
            props = request.env['smileliving.property'].sudo().search([
                ('product_tmpl_id', 'in', products.ids)
            ])
            properties_by_template_id = {p.product_tmpl_id.id: p for p in props}

        response.qcontext['smileliving_properties_by_template_id'] = properties_by_template_id
        
        return response

    @http.route('/smileliving/get_quanhuyen', type='json', auth='public', website=True)
    def get_quanhuyen(self, tinhthanh_id):
        """API để load quận huyện theo tỉnh thành"""
        if tinhthanh_id:
            quanhuyens = request.env['quan.huyen'].sudo().search([
                ('tinhthanh_id', '=', int(tinhthanh_id)),
                ('active', '=', True)
            ], order='name')
            return [{'id': q.id, 'name': q.name} for q in quanhuyens]
        return []

    @http.route('/smileliving/get_phuongxa', type='json', auth='public', website=True)
    def get_phuongxa(self, quanhuyen_id):
        """API để load phường xã theo quận huyện"""
        if quanhuyen_id:
            phuongxas = request.env['phuong.xa'].sudo().search([
                ('quanhuyen_id', '=', int(quanhuyen_id)),
                ('active', '=', True)
            ], order='name')
            return [{'id': p.id, 'name': p.name} for p in phuongxas]
        return []
