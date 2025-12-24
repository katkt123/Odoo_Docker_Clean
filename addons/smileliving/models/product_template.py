from odoo import api, models
from odoo.http import request


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _search_get_detail(self, website, order, options):
        """Inject SmileLiving /shop filters into the products_only fuzzy search domain.

        In Odoo 19, /shop uses website._search_with_fuzzy('products_only', ...) which relies on
        product.template._search_get_detail() to build the base domain.
        """
        detail = super()._search_get_detail(website, order, options)

        httprequest = getattr(request, 'httprequest', None)
        path = getattr(httprequest, 'path', '') or ''
        if not path.startswith('/shop'):
            return detail

        args = getattr(httprequest, 'args', {}) or {}

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

        extra_domain = [
            ('is_house', '=', True),
        ]

        # Location filters
        tinhthanh_id = _safe_int(_first(args.get('tinhthanh_id', '')))
        quanhuyen_id = _safe_int(_first(args.get('quanhuyen_id', '')))
        phuongxa_id = _safe_int(_first(args.get('phuongxa_id', '')))
        if tinhthanh_id:
            extra_domain.append(('tinhthanh_id', '=', tinhthanh_id))
        if quanhuyen_id:
            extra_domain.append(('quanhuyen_id', '=', quanhuyen_id))
        if phuongxa_id:
            extra_domain.append(('phuongxa_id', '=', phuongxa_id))

        # Custom filters (multi select)
        filter_type_ids = []
        if hasattr(args, 'getlist'):
            filter_type_ids = [_safe_int(v) for v in args.getlist('filter_type_id')]
        else:
            filter_type_ids = [_safe_int(_first(args.get('filter_type_id', '')))]
        filter_type_ids = [v for v in filter_type_ids if v]
        if filter_type_ids:
            extra_domain.append(('type_id', 'in', tuple(filter_type_ids)))

        # Amenity filters (multi select)
        filter_amenity_ids = []
        if hasattr(args, 'getlist'):
            filter_amenity_ids = [_safe_int(v) for v in args.getlist('filter_amenity_id')]
        else:
            filter_amenity_ids = [_safe_int(_first(args.get('filter_amenity_id', '')))]
        filter_amenity_ids = [v for v in filter_amenity_ids if v]
        if filter_amenity_ids:
            extra_domain.append(('amenity_ids', 'in', tuple(filter_amenity_ids)))

        type_sale = _first(args.get('type_sale', ''))
        if type_sale in ('sale', 'rent'):
            extra_domain.append(('type_sale', '=', type_sale))

        filter_area_min = _safe_float(_first(args.get('filter_area_min', '')))
        filter_area_max = _safe_float(_first(args.get('filter_area_max', '')))
        if filter_area_min is not None:
            extra_domain.append(('area', '>=', filter_area_min))
        if filter_area_max is not None:
            extra_domain.append(('area', '<=', filter_area_max))

        # (Removed) price filtering

        def _is_flat_domain_list(dom):
            if not isinstance(dom, list):
                return False
            # A flat domain list contains leaves (tuples) and/or operator tokens ('&', '|', '!')
            return any(
                isinstance(item, str)
                or (isinstance(item, tuple) and len(item) == 3)
                for item in dom
            )

        base_domain = detail.get('base_domain')

        # Odoo website search expects: base_domain = [domain1, domain2, ...]
        # where each item is a domain (list/tuple/Domain), not a single combined domain.
        if not base_domain:
            domain_list = []
        elif isinstance(base_domain, list):
            domain_list = [base_domain] if _is_flat_domain_list(base_domain) else base_domain
        else:
            # Domain object or any other supported representation: wrap as a single item
            domain_list = [base_domain]

        domain_list.append(extra_domain)
        detail['base_domain'] = domain_list

        return detail

