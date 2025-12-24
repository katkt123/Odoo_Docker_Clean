import urllib.parse

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SmileLivingProperty(models.Model):
    _name = 'smileliving.property'
    _description = 'Bất Động Sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Sản phẩm (Product Template)',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    # Images are stored on product.template (and product.image for extra media).
    # Expose them here so users can manage images directly from the property UI.
    product_image_1920 = fields.Image(
        string='Ảnh đại diện',
        related='product_tmpl_id.image_1920',
        readonly=False,
    )

    product_template_image_ids = fields.One2many(
        related='product_tmpl_id.product_template_image_ids',
        string='Media eCommerce',
        readonly=False,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        related='product_tmpl_id.company_id',
        store=True,
        readonly=True,
    )

    type_id = fields.Many2one(
        'smileliving.type',
        string='Danh Mục Bất Động Sản',
        tracking=True,
    )

    type_sale = fields.Selection(
        [
            ('sale', 'Mua bán'),
            ('rent', 'Cho thuê'),
        ],
        string='Loại',
        default='sale',
        tracking=True,
    )

    area = fields.Float(
        string='Diện Tích (m²)',
        required=True,
        tracking=True,
        digits=(10, 2),
    )

    house_status = fields.Selection(
        [
            ('available', 'Còn Trống'),
            ('reserved', 'Đã Giữ'),
            ('sold', 'Đã Bán'),
            ('maintenance', 'Bảo Trì'),
        ],
        string='Trạng Thái',
        default='available',
        tracking=True,
    )

    description_detail = fields.Text(string='Mô Tả Chi Tiết')

    address = fields.Text(string='Địa Chỉ', tracking=True)

    tinhthanh_id = fields.Many2one('tinh.thanh', string='Tỉnh/Thành phố', tracking=True)
    quanhuyen_id = fields.Many2one('quan.huyen', string='Quận/Huyện', tracking=True)
    phuongxa_id = fields.Many2one('phuong.xa', string='Phường/Xã', tracking=True)

    amenity_ids = fields.Many2many(
        'smileliving.amenity',
        'smileliving_property_amenity_rel',
        'property_id',
        'amenity_id',
        string='Tiện Ích',
        tracking=True,
        help='Các tiện ích của bất động sản (chọn nhiều).',
    )

    latitude = fields.Float(string='Vĩ Độ', digits=(10, 6))
    longitude = fields.Float(string='Kinh Độ', digits=(10, 6))

    google_maps_url = fields.Char(string='Google Maps URL', compute='_compute_google_maps_urls', store=True)
    google_maps_embed_url = fields.Char(string='Google Maps Embed URL', compute='_compute_google_maps_urls', store=True)
    google_maps_iframe = fields.Html(
        string='Google Maps Iframe',
        compute='_compute_google_maps_iframe',
        store=True,
        sanitize=False,
    )

    @api.constrains('product_tmpl_id')
    def _check_unique_product_tmpl(self):
        for rec in self:
            if not rec.product_tmpl_id:
                continue
            dup = self.search([
                ('id', '!=', rec.id),
                ('product_tmpl_id', '=', rec.product_tmpl_id.id),
            ], limit=1)
            if dup:
                raise ValidationError('Mỗi product.template chỉ được gắn với 1 smileliving.property.')

    # -------------------------------------------------------------------------
    # Demo reset & seed (VN Real Estate) - for test projects
    # -------------------------------------------------------------------------

    @api.model
    def _cron_reset_and_seed_vn_demo(self):
        """One-time cron job to replace demo e-commerce catalog with VN real-estate demo data.

        This is designed for TEST databases without backups.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('smileliving.vn_demo_seeded'):
            cron = self.env.ref('smileliving.ir_cron_smileliving_reset_seed_vn_demo', raise_if_not_found=False)
            if cron:
                cron.active = False
            return

        self._reset_and_seed_vn_demo(hard_delete=False)

        ICP.set_param('smileliving.vn_demo_seeded', '1')
        cron = self.env.ref('smileliving.ir_cron_smileliving_reset_seed_vn_demo', raise_if_not_found=False)
        if cron:
            cron.active = False

    @api.model
    def reset_and_seed_vn_demo(self, hard_delete=False):
        """Manual entrypoint (can be called from Odoo shell).

        - `hard_delete=False` (default): unpublish + archive demo products.
        - `hard_delete=True`: try unlinking demo products (risky).
        """
        self._reset_and_seed_vn_demo(hard_delete=bool(hard_delete))

    @api.model
    def _reset_and_seed_vn_demo(self, hard_delete=False):
        company = self._seed_target_company()
        self._reset_demo_catalog(company, hard_delete=hard_delete)
        self._delete_previous_seed(company, hard_delete=hard_delete)
        self._seed_vn_real_estate(company)

    @api.model
    def _seed_target_company(self):
        website = self.env['website'].sudo().search([], limit=1)
        if website and website.company_id:
            return website.company_id
        return self.env.company

    @api.model
    def _delete_previous_seed(self, company, hard_delete=False):
        ProductTmpl = self.env['product.template'].sudo().with_company(company)
        seeded = ProductTmpl.search([
            ('company_id', 'in', [company.id, False]),
            ('product_variant_ids.default_code', '=ilike', 'VNRE-%'),
        ])

        props = self.sudo().search([
            ('company_id', 'in', [company.id, False]),
            ('product_tmpl_id', 'in', seeded.ids),
        ])

        # Default behavior: do NOT hard-delete templates/variants because they may be
        # referenced by wishlists/orders/etc. (this method runs from a cron).
        if not hard_delete:
            if seeded:
                vals = {'active': False}
                if 'is_published' in ProductTmpl._fields:
                    vals['is_published'] = False
                if 'website_published' in ProductTmpl._fields:
                    vals['website_published'] = False
                seeded.write(vals)
            if props:
                props.unlink()
            return

        # Hard delete (best-effort): remove wishlist references first.
        variant_ids = seeded.mapped('product_variant_ids').ids
        if variant_ids:
            try:
                Wishlist = self.env['product.wishlist'].sudo()
            except KeyError:
                Wishlist = None
            if Wishlist:
                Wishlist.search([('product_id', 'in', variant_ids)]).unlink()

        try:
            if props:
                props.unlink()
            if seeded:
                seeded.unlink()
        except Exception:
            # Fall back to archive/unpublish so the cron doesn't keep failing.
            if seeded:
                vals = {'active': False}
                if 'is_published' in ProductTmpl._fields:
                    vals['is_published'] = False
                if 'website_published' in ProductTmpl._fields:
                    vals['website_published'] = False
                seeded.write(vals)
            if props:
                props.unlink()

    @api.model
    def _reset_demo_catalog(self, company, hard_delete=False):
        """Remove/disable existing published shop items (desk, box, etc.).

        By default we *archive + unpublish* to avoid breaking references.
        """
        # Intentionally global across companies: demo products often belong to the
        # original company (e.g. Main Company) but still appear in the shop of a
        # test database.
        ProductTmpl = self.env['product.template'].sudo()

        # Avoid relying on domains like
        #   ('product_variant_ids.default_code', 'not ilike', 'VNRE-%')
        # because templates with empty/NULL default_code can be missed.
        published = ProductTmpl.search([
            ('sale_ok', '=', True),
            ('is_published', '=', True),
        ])
        vnre_templates = published.filtered(
            lambda t: any((v.default_code or '').upper().startswith('VNRE-') for v in t.product_variant_ids)
        )
        demo_products = published - vnre_templates

        if not demo_products:
            return

        if hard_delete:
            # Best-effort: will fail if referenced by orders/invoices.
            try:
                demo_products.unlink()
                return
            except Exception:
                # Fall back to archive/unpublish.
                pass

        vals = {'active': False}
        if 'is_published' in ProductTmpl._fields:
            vals['is_published'] = False
        if 'website_published' in ProductTmpl._fields:
            vals['website_published'] = False
        demo_products.write(vals)

    @api.model
    def _seed_vn_real_estate(self, company):
        """Create VN real-estate demo: categories, amenities, types, products + properties."""
        env = self.env
        ProductTmpl = env['product.template'].sudo().with_company(company)
        PublicCateg = env['product.public.category'].sudo()
        Type = env['smileliving.type'].sudo()
        Amenity = env['smileliving.amenity'].sudo()

        root_categ = PublicCateg.search([('name', '=', 'Bất động sản')], limit=1)
        if not root_categ:
            root_categ = PublicCateg.create({'name': 'Bất động sản'})

        def _child(name):
            rec = PublicCateg.search([('name', '=', name), ('parent_id', '=', root_categ.id)], limit=1)
            if not rec:
                rec = PublicCateg.create({'name': name, 'parent_id': root_categ.id})
            return rec

        categ_apartment = _child('Căn hộ chung cư')
        categ_house = _child('Nhà ở')
        categ_land = _child('Đất nền')
        categ_villa = _child('Biệt thự')
        categ_shophouse = _child('Shophouse')

        amenity_names = [
            'Bảo vệ 24/7',
            'Hồ bơi',
            'Phòng gym',
            'Bãi đậu xe',
            'Thang máy',
            'Sân chơi trẻ em',
            'Công viên nội khu',
            'Gần trường học',
            'Gần bệnh viện',
            'Nội thất cơ bản',
        ]
        amenities = {}
        for name in amenity_names:
            rec = Amenity.search([('name', '=', name)], limit=1)
            if not rec:
                rec = Amenity.create({'name': name})
            amenities[name] = rec

        def _type(name, amenity_list):
            rec = Type.search([('name', '=', name)], limit=1)
            if not rec:
                rec = Type.create({'name': name})
            rec.amenity_ids = [(6, 0, [amenities[a].id for a in amenity_list if a in amenities])]
            return rec

        t_apartment = _type('Căn hộ chung cư', ['Bảo vệ 24/7', 'Hồ bơi', 'Phòng gym', 'Bãi đậu xe', 'Thang máy', 'Sân chơi trẻ em'])
        t_house = _type('Nhà phố', ['Bãi đậu xe', 'Gần trường học', 'Gần bệnh viện', 'Nội thất cơ bản'])
        t_villa = _type('Biệt thự', ['Công viên nội khu', 'Bảo vệ 24/7', 'Hồ bơi', 'Bãi đậu xe'])
        t_land = _type('Đất nền', ['Gần trường học', 'Gần bệnh viện'])
        t_shophouse = _type('Shophouse', ['Bảo vệ 24/7', 'Bãi đậu xe', 'Công viên nội khu'])

        samples = [
            {
                'code': 'VNRE-0001',
                'name': 'Căn hộ 2PN Vinhomes Grand Park',
                'price': 2650000000,
                'area': 68.5,
                'type_id': t_apartment.id,
                'type_sale': 'sale',
                'categ': categ_apartment,
                'address': 'TP. Thủ Đức, TP. Hồ Chí Minh',
                'lat': 10.8429,
                'lng': 106.8287,
            },
            {
                'code': 'VNRE-0002',
                'name': 'Căn hộ 1PN Masteri Thảo Điền',
                'price': 3950000000,
                'area': 52.0,
                'type_id': t_apartment.id,
                'type_sale': 'sale',
                'categ': categ_apartment,
                'address': 'Thảo Điền, TP. Thủ Đức, TP. Hồ Chí Minh',
                'lat': 10.8049,
                'lng': 106.7366,
            },
            {
                'code': 'VNRE-0003',
                'name': 'Nhà phố 1 trệt 2 lầu Quận 7',
                'price': 7850000000,
                'area': 92.0,
                'type_id': t_house.id,
                'type_sale': 'sale',
                'categ': categ_house,
                'address': 'Quận 7, TP. Hồ Chí Minh',
                'lat': 10.7367,
                'lng': 106.7219,
            },
            {
                'code': 'VNRE-0004',
                'name': 'Biệt thự sân vườn Thảo Điền',
                'price': 38500000000,
                'area': 240.0,
                'type_id': t_villa.id,
                'type_sale': 'sale',
                'categ': categ_villa,
                'address': 'Thảo Điền, TP. Thủ Đức, TP. Hồ Chí Minh',
                'lat': 10.8062,
                'lng': 106.7338,
            },
            {
                'code': 'VNRE-0005',
                'name': 'Đất nền KDC Long An (sổ riêng)',
                'price': 1450000000,
                'area': 100.0,
                'type_id': t_land.id,
                'type_sale': 'sale',
                'categ': categ_land,
                'address': 'Đức Hòa, Long An',
                'lat': 10.8739,
                'lng': 106.4253,
            },
            {
                'code': 'VNRE-0006',
                'name': 'Shophouse mặt tiền khu đô thị',
                'price': 12500000000,
                'area': 120.0,
                'type_id': t_shophouse.id,
                'type_sale': 'sale',
                'categ': categ_shophouse,
                'address': 'TP. Thủ Đức, TP. Hồ Chí Minh',
                'lat': 10.8203,
                'lng': 106.7606,
            },
            {
                'code': 'VNRE-0007',
                'name': 'Căn hộ 2PN cho thuê Quận Bình Thạnh',
                'price': 18000000,
                'area': 70.0,
                'type_id': t_apartment.id,
                'type_sale': 'rent',
                'categ': categ_apartment,
                'address': 'Bình Thạnh, TP. Hồ Chí Minh',
                'lat': 10.8106,
                'lng': 106.7091,
            },
        ]

        for s in samples:
            tmpl_vals = {
                'name': s['name'],
                'sale_ok': True,
                'purchase_ok': False,
                'company_id': company.id,
                'list_price': float(s['price']),
                'public_categ_ids': [(6, 0, [root_categ.id, s['categ'].id])],
            }
            if 'is_published' in ProductTmpl._fields:
                tmpl_vals['is_published'] = True
            elif 'website_published' in ProductTmpl._fields:
                tmpl_vals['website_published'] = True

            # Odoo versions differ: detailed_type (new) vs type (old)
            if 'detailed_type' in ProductTmpl._fields:
                tmpl_vals['detailed_type'] = 'service'
            elif 'type' in ProductTmpl._fields:
                tmpl_vals['type'] = 'service'

            tmpl = ProductTmpl.create(tmpl_vals)
            if tmpl.product_variant_id:
                tmpl.product_variant_id.default_code = s['code']

            prop_vals = {
                'product_tmpl_id': tmpl.id,
                'type_id': s['type_id'],
                'type_sale': s['type_sale'],
                'area': float(s['area']),
                'house_status': 'available',
                'address': s['address'],
                'latitude': float(s['lat']),
                'longitude': float(s['lng']),
                'amenity_ids': [(6, 0, Type.browse(s['type_id']).amenity_ids.ids)],
            }
            self.sudo().create(prop_vals)

    @api.depends(
        'latitude',
        'longitude',
        'address',
        'tinhthanh_id',
        'quanhuyen_id',
        'phuongxa_id',
    )
    def _compute_google_maps_urls(self):
        for rec in self:
            query = (rec.address or '').strip()
            if not query:
                parts = [
                    (rec.phuongxa_id.name if rec.phuongxa_id else ''),
                    (rec.quanhuyen_id.name if rec.quanhuyen_id else ''),
                    (rec.tinhthanh_id.name if rec.tinhthanh_id else ''),
                ]
                query = ', '.join([p for p in parts if p])

            if rec.latitude and rec.longitude:
                q = f"{rec.latitude},{rec.longitude}"
            elif query:
                q = urllib.parse.quote_plus(query)
            else:
                q = None

            if q:
                rec.google_maps_url = f"https://www.google.com/maps?q={q}"
                rec.google_maps_embed_url = f"https://www.google.com/maps?q={q}&output=embed"
            else:
                rec.google_maps_url = False
                rec.google_maps_embed_url = False

    @api.depends('google_maps_embed_url')
    def _compute_google_maps_iframe(self):
        for rec in self:
            if rec.google_maps_embed_url:
                rec.google_maps_iframe = (
                    f"<iframe width=\"100%\" height=\"400\" src=\"{rec.google_maps_embed_url}\" "
                    f"style=\"border:0;\" allowfullscreen=\"\"></iframe>"
                )
            else:
                rec.google_maps_iframe = "<div>Không có bản đồ</div>"

    @api.onchange('tinhthanh_id')
    def _onchange_tinhthanh_id(self):
        if self.tinhthanh_id:
            self.quanhuyen_id = False
            self.phuongxa_id = False

    @api.onchange(
        'address',
        'tinhthanh_id',
        'quanhuyen_id',
        'phuongxa_id',
        'latitude',
        'longitude',
    )
    def _onchange_address_or_coords_preview_map(self):
        # Stored computed fields may not refresh in the form until save.
        # Force a live preview update for the backend UI.
        self._compute_google_maps_urls()
        self._compute_google_maps_iframe()

    @api.onchange('quanhuyen_id')
    def _onchange_quanhuyen_id(self):
        if self.quanhuyen_id:
            self.phuongxa_id = False
