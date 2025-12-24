# from odoo import models, fields, api, _
# import requests

# class HouseProperty(models.Model):
#     _name = 'smileliving.house'
#     _description = 'Bất Động Sản'
#     _inherit = ['mail.thread', 'mail.activity.mixin']

#     name = fields.Char(string='Tên Bất Động Sản', required=True, tracking=True, help="Tên của bất động sản")
#     type_id = fields.Many2one('smileliving.type', string='Loại Bất Động Sản', required=True, tracking=True, help="Loại bất động sản với các tiện ích")
#     price = fields.Float(string='Giá', required=True, tracking=True, digits=(16, 2), help="Giá bất động sản")
#     area = fields.Float(string='Diện Tích (m²)', required=True, tracking=True, digits=(10, 2), help="Diện tích bất động sản tính bằng mét vuông")
#     status = fields.Selection([('available', 'Còn Trống'), ('reserved', 'Đã Giữ'), ('sold', 'Đã Bán'), ('maintenance', 'Bảo Trì')],
#                               string='Trạng Thái', default='available', required=True, tracking=True, help="Trạng thái hiện tại của bất động sản")
#     image = fields.Image(string='Hình Ảnh', max_width=1024, max_height=1024, help="Hình ảnh bất động sản")
#     description = fields.Text(string='Mô Tả', tracking=True, help="Mô tả chi tiết về bất động sản")
#     address = fields.Text(string='Địa Chỉ', required=True, tracking=True, help="Địa chỉ đầy đủ của bất động sản")
#     latitude = fields.Float(string='Vĩ Độ', digits=(10, 6), help="Vĩ độ của bất động sản")
#     longitude = fields.Float(string='Kinh Độ', digits=(10, 6), help="Kinh độ của bất động sản")
#     google_maps_url = fields.Char(string='Google Maps', compute='_compute_google_maps_url', store=True)
#     google_maps_embed_url = fields.Char(string='Google Maps Embed', compute='_compute_google_maps_embed_url', store=True)
#     google_maps_iframe = fields.Html(string='Google Maps Iframe', compute='_compute_google_maps_iframe', store=True)
#     active = fields.Boolean(string='Hoạt Động', default=True, help="Kích hoạt/vô hiệu hóa bản ghi")
#     created_date = fields.Datetime(string='Ngày Tạo', default=fields.Datetime.now, readonly=True)
#     invoice_count = fields.Integer(string='Số Hóa Đơn', compute='_compute_invoice_count', store=True)

#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if 'name' not in vals or not vals['name']:
#                 vals['name'] = self.env['ir.sequence'].next_by_code('smileliving.house') or 'Bất Động Sản Mới'
#         return super(HouseProperty, self).create(vals_list)

#     @api.depends('latitude', 'longitude')
#     def _compute_google_maps_url(self):
#         for record in self:
#             if record.latitude and record.longitude:
#                 record.google_maps_url = f'https://www.google.com/maps?q={record.latitude},{record.longitude}'
#             else:
#                 record.google_maps_url = False

#     @api.depends('latitude', 'longitude')
#     def _compute_google_maps_embed_url(self):
#         for record in self:
#             if record.latitude and record.longitude:
#                 record.google_maps_embed_url = f'https://www.google.com/maps?q={record.latitude},{record.longitude}&output=embed'
#             else:
#                 record.google_maps_embed_url = False

#     @api.depends('latitude', 'longitude')
#     def _compute_google_maps_iframe(self):
#         for record in self:
#             if record.latitude and record.longitude:
#                 embed_url = f'https://www.google.com/maps?q={record.latitude},{record.longitude}&output=embed'
#                 record.google_maps_iframe = f'<iframe width="100%" height="400" src="{embed_url}" style="border:0;" frameborder="0" allowfullscreen="true"></iframe>'
#             else:
#                 record.google_maps_iframe = '<div style="padding: 20px; text-align: center; color: #666;">Chưa có tọa độ để hiển thị bản đồ</div>'

#     @api.depends('name')
#     def _compute_invoice_count(self):
#         """Compute invoice count"""
#         for property in self:
#             property.invoice_count = self.env['smileliving.invoice'].search_count([('property_id', '=', property.id)])

#     def action_sold(self):
#         self.status = 'sold'
#         self.message_post(body=_("Bất động sản đã được bán"))

#     def action_reserve(self):
#         self.status = 'reserved'
#         self.message_post(body=_("Bất động sản đã được giữ"))

#     def action_available(self):
#         self.status = 'available'
#         self.message_post(body=_("Bất động sản đã có sẵn"))

#     def action_view_invoices(self):
#         """View invoices related to this property"""
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Hóa Đơn',
#             'res_model': 'smileliving.invoice',
#             'view_mode': 'list,form',
#             'domain': [('property_id', '=', self.id)],
#             'context': {'default_property_id': self.id},
#         }

#     def action_open_map_popup(self):
#         """Open Google Maps in new window"""
#         if self.google_maps_url:
#             return {
#                 'type': 'ir.actions.act_url',
#                 'url': self.google_maps_url,
#                 'target': 'new',
#             }
#         return False

#     def action_create_crm_lead(self):
#         lead_name = f"Quan tâm: {self.name} - {self.address}"

#         description = f"""
#         Khách hàng quan tâm bất động sản:
#         - Tên: {self.name}
#         - Địa chỉ: {self.address}
#         - Giá: {self.price:,.0f} VNĐ
#         - Diện tích: {self.area} m²
#         - Loại hình: {self.type_id.name if self.type_id else 'Chưa xác định'}
#         - Trạng thái: {dict(self._fields['status'].selection).get(self.status)}
#         """

#         lead_vals = {
#             'name': lead_name,
#             'description': description,
#             'priority': '2',    # High
#         }

        
#         if self.env.user and not self.env.user._is_public():
#             lead_vals['partner_id'] = self.env.user.partner_id.id

#         lead = self.env['crm.lead'].sudo().create(lead_vals)

#         self.message_post(body=f"Đã tạo CRM Lead <a href='#' data-oe-model='crm.lead' data-oe-id='{lead.id}'>{lead.name}</a>")
#         return {
#             'success': True,
#             'lead_id': lead.id,
#             'lead_name': lead.name,
#             'message': f"Đã tạo lead: {lead.name}"
#         }

#     @api.onchange('address')
#     def _onchange_address(self):
#         if self.address:
#             try:
#                 url = "https://nominatim.openstreetmap.org/search"
#                 response = requests.get(url, params={
#                     "q": self.address,
#                     "format": "json"
#                 }, headers={"User-Agent": "Odoo"}, timeout=5)
#                 if response.status_code == 200 and response.json():
#                     pos = response.json()[0]
#                     self.latitude = float(pos["lat"])
#                     self.longitude = float(pos["lon"])
#                 else:
#                     self.latitude = False
#                     self.longitude = False
#             except Exception:
#                 self.latitude = False
#                 self.longitude = False
# -----------------------------------------------------------------------------------------
from odoo import models, fields, api, _
from odoo.http import request
import requests

class HouseProduct(models.Model):
    _inherit = 'product.template'
    # _description = 'Bất Động Sản'

    # Xác định đây là sản phẩm bất động sản
    is_house = fields.Boolean(string='Là Bất Động Sản', default=True)

    # Loại bất động sản
    type_id = fields.Many2one(
        'smileliving.type',
        string='Danh Mục Bất Động Sản',
        required=False,
        tracking=True,
    )

    # Loại giao dịch
    type_sale = fields.Selection(
        [
            ('sale', 'Mua bán'),
            ('rent', 'Cho thuê'),
        ],
        string='Loại',
        default='sale',
        tracking=True,
    )

    # Giá sẽ dùng list_price của product.template
    # Không cần tạo field price nữa

    # Diện tích
    area = fields.Float(
        string='Diện Tích (m²)',
        required=True,
        tracking=True,
        digits=(10, 2),
    )

    # Trạng thái
    house_status = fields.Selection([
        ('available', 'Còn Trống'),
        ('reserved', 'Đã Giữ'),
        ('sold', 'Đã Bán'),
        ('maintenance', 'Bảo Trì')
    ],
        string='Trạng Thái',
        default='available',
        tracking=True
    )

    # Hình ảnh: product.template đã có image_1920, image_1024,...
    # Bạn KHÔNG cần định nghĩa lại field image

    description_detail = fields.Text(
        string='Mô Tả Chi Tiết'
    )

    address = fields.Text(
        string='Địa Chỉ',
        required=False,
        tracking=True,
    )

    # Thông tin địa lý Việt Nam
    tinhthanh_id = fields.Many2one(
        'tinh.thanh',
        string='Tỉnh/Thành phố',
        tracking=True,
    )
    quanhuyen_id = fields.Many2one(
        'quan.huyen', 
        string='Quận/Huyện',
        tracking=True,
    )
    phuongxa_id = fields.Many2one(
        'phuong.xa',
        string='Phường/Xã',
        tracking=True,
    )

    amenity_ids = fields.Many2many(
        'smileliving.amenity',
        'smileliving_product_template_amenity_rel',
        'product_tmpl_id',
        'amenity_id',
        string='Tiện Ích',
        tracking=True,
        help='Các tiện ích của bất động sản (chọn nhiều).',
    )

    bedroom_count = fields.Integer(
        string='Phòng ngủ',
        tracking=True,
        default=0,
    )

    bathroom_count = fields.Integer(
        string='WC',
        tracking=True,
        default=0,
    )

    house_direction = fields.Selection(
        [
            ('n', 'Bắc'),
            ('ne', 'Đông Bắc'),
            ('e', 'Đông'),
            ('se', 'Đông Nam'),
            ('s', 'Nam'),
            ('sw', 'Tây Nam'),
            ('w', 'Tây'),
            ('nw', 'Tây Bắc'),
        ],
        string='Hướng',
        tracking=True,
    )

    legal_status = fields.Selection(
        [
            ('so_hong', 'Sổ hồng'),
            ('so_do', 'Sổ đỏ'),
            ('hop_dong', 'Hợp đồng'),
            ('dang_cho', 'Đang chờ'),
            ('khac', 'Khác'),
        ],
        string='Pháp lý',
        tracking=True,
    )

    furnishing = fields.Selection(
        [
            ('none', 'Không nội thất'),
            ('basic', 'Nội thất cơ bản'),
            ('full', 'Full nội thất'),
        ],
        string='Nội thất',
        tracking=True,
    )

    floor_count = fields.Integer(
        string='Số tầng',
        tracking=True,
        default=0,
    )

    frontage = fields.Float(
        string='Mặt tiền (m)',
        tracking=True,
        digits=(10, 2),
    )

    build_year = fields.Integer(
        string='Năm xây',
        tracking=True,
    )

    def _sync_categories_from_type(self):
        """Sync eCommerce 'Categories' (public_categ_ids) from selected real-estate type."""
        for rec in self:
            if not rec.is_house or not rec.type_id:
                continue

            type_name = (rec.type_id.name or '').strip()
            if not type_name:
                continue

            PublicCateg = self.env['product.public.category'].sudo()
            target_public = PublicCateg.search([('name', '=', type_name)], limit=1)
            if not target_public:
                target_public = PublicCateg.create({'name': type_name})

            current_public = rec.public_categ_ids
            if (len(current_public) != 1) or (current_public.id != target_public.id):
                # Avoid recursion by writing only when needed
                super(HouseProduct, rec).write({'public_categ_ids': [(6, 0, [target_public.id])]})

    @api.onchange('type_id')
    def _onchange_type_id_sync_categories(self):
        for rec in self:
            if not rec.is_house or not rec.type_id:
                continue

            type_name = (rec.type_id.name or '').strip()
            if not type_name:
                continue

            PublicCateg = self.env['product.public.category'].sudo()
            target_public = PublicCateg.search([('name', '=', type_name)], limit=1)
            if not target_public:
                target_public = PublicCateg.create({'name': type_name})

            rec.public_categ_ids = [(6, 0, [target_public.id])]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Default to current company so monetary fields (e.g., list_price) use the right currency.
            # Without this, company_id may stay empty (shared product) and the UI may show USD.
            vals.setdefault('company_id', self.env.company.id)

        records = super().create(vals_list)
        records._sync_categories_from_type()
        return records

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Make the company explicit on new records so Sales Price shows in the company currency.
        if 'company_id' in fields_list and not res.get('company_id'):
            res['company_id'] = self.env.company.id
        return res

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('type_id', 'is_house')):
            self._sync_categories_from_type()
        return res

    @api.onchange('is_house')
    def _onchange_is_house(self):
        for rec in self:
            if rec.is_house:
                rec.sale_ok = True
                rec.purchase_ok = False

    @api.onchange('tinhthanh_id')
    def _onchange_tinhthanh_id(self):
        """Khi thay đổi tỉnh thành, xóa quận huyện và phường xã"""
        if self.tinhthanh_id:
            self.quanhuyen_id = False
            self.phuongxa_id = False

    @api.onchange('quanhuyen_id')
    def _onchange_quanhuyen_id(self):
        """Khi thay đổi quận huyện, xóa phường xã"""
        if self.quanhuyen_id:
            self.phuongxa_id = False

    # Google Map
    latitude = fields.Float(
        string='Vĩ Độ',
        digits=(10, 6)
    )
    longitude = fields.Float(
        string='Kinh Độ',
        digits=(10, 6)
    )

    google_maps_url = fields.Char(
        string='Google Maps URL',
        compute='_compute_google_maps_url',
        store=True,
    )

    google_maps_embed_url = fields.Char(
        string='Google Maps Embed URL',
        compute='_compute_google_maps_embed_url',
        store=True,
    )

    google_maps_iframe = fields.Html(
        string='Google Maps Iframe',
        compute='_compute_google_maps_iframe',
        store=True,
    )

    # Invoice Count
    invoice_count = fields.Integer(
        string='Số Hóa Đơn',
        compute='_compute_invoice_count',
        store=True,
    )

    # =====================================================================
    # GOOGLE MAP COMPUTE
    # =====================================================================

    @api.depends('latitude', 'longitude')
    def _compute_google_maps_url(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                rec.google_maps_url = f"https://www.google.com/maps?q={rec.latitude},{rec.longitude}"
            else:
                rec.google_maps_url = False

    @api.depends('latitude', 'longitude')
    def _compute_google_maps_embed_url(self):
        for rec in self:
            if rec.latitude and rec.longitude:
                rec.google_maps_embed_url = (
                    f"https://www.google.com/maps?q={rec.latitude},{rec.longitude}&output=embed"
                )
            else:
                rec.google_maps_embed_url = False

    @api.depends('google_maps_embed_url')
    def _compute_google_maps_iframe(self):
        for rec in self:
            if rec.google_maps_embed_url:
                rec.google_maps_iframe = f"""
                <iframe width="100%" height="400" 
                        src="{rec.google_maps_embed_url}"
                        style="border:0;" allowfullscreen=""></iframe>
                """
            else:
                rec.google_maps_iframe = "<div>Không có bản đồ</div>"

    # =====================================================================
    # HÓA ĐƠN
    # =====================================================================

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['smileliving.invoice'].search_count([
                ('property_id', '=', rec.id)
            ])

    # =====================================================================
    # NÚT HÀNH ĐỘNG
    # =====================================================================

    def action_sold(self):
        self.house_status = 'sold'
        self.message_post(body=_("Bất động sản đã được bán."))

    def action_reserve(self):
        self.house_status = 'reserved'
        self.message_post(body=_("Bất động sản đã được giữ chỗ."))

    def action_available(self):
        self.house_status = 'available'
        self.message_post(body=_("Bất động sản đã mở bán trở lại."))

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hóa Đơn',
            'res_model': 'smileliving.invoice',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_open_map_popup(self):
        if self.google_maps_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.google_maps_url,
                'target': 'new'
            }
        return False

    def action_create_crm_lead(self):
        lead_vals = {
            'name': f"Quan tâm: {self.name}",
            'description': f"""
                Bất động sản:
                - Tên: {self.name}
                - Địa chỉ: {self.address}
                - Giá: {self.list_price:,.0f} VNĐ
                - Diện tích: {self.area} m²
                - Trạng thái: {self.house_status}
            """,
            'priority': '2',
        }
        lead = self.env['crm.lead'].sudo().create(lead_vals)
        self.message_post(body=f"Đã tạo CRM Lead {lead.name}")
        return lead

    # =====================================================================
    # AUTO GEO FROM ADDRESS
    # =====================================================================

    @api.onchange('address')
    def _onchange_address(self):
        if not self.address:
            return

        LOCATIONIQ_KEY = "pk.f6448c49853ec2d3bace35e9a1018c56"

        try:
            url = "https://us1.locationiq.com/v1/search"
            params = {
                "key": LOCATIONIQ_KEY,
                "q": self.address,
                "format": "json",
                "limit": 5,             # lấy nhiều kết quả
                "countrycodes": "vn",
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                best = data[0]     # → lấy kết quả “best match”
                self.latitude = float(best["lat"])
                self.longitude = float(best["lon"])
            else:
                self.latitude = False
                self.longitude = False

        except Exception:
            self.latitude = False
            self.longitude = False

    # =====================================================================
    # OVERRIDE SEARCH FOR FILTER
    # =====================================================================

    @api.model
    def _search_get_detail(self, website, order, options):
        """Override để thêm filter SmileLiving vào search domain"""
        result = super()._search_get_detail(website, order, options)
        
        # Lấy filter parameters từ request
        if not request:
            return result
            
        request_args = request.httprequest.args if hasattr(request, 'httprequest') else {}
        filter_type_id = request_args.get('filter_type_id', '')
        filter_status = request_args.get('filter_status', '')
        filter_area_min = request_args.get('filter_area_min', '')
        filter_area_max = request_args.get('filter_area_max', '')
        filter_price_min = request_args.get('filter_price_min', '')
        filter_price_max = request_args.get('filter_price_max', '')
        
        # Xử lý nếu là list
        if isinstance(filter_type_id, list):
            filter_type_id = filter_type_id[0] if filter_type_id else ''
        if isinstance(filter_status, list):
            filter_status = filter_status[0] if filter_status else ''
        
        # Lấy domains từ result - đảm bảo là list
        domains = result.get('base_domain', [])
        if not isinstance(domains, list):
            domains = [domains] if domains else []
        
        # Chỉ hiển thị sản phẩm BĐS
        domains.append([('is_house', '=', True)])
        
        # Filter theo loại BĐS
        if filter_type_id:
            try:
                domains.append([('type_id', '=', int(filter_type_id))])
            except (ValueError, TypeError):
                pass
        
        # Filter theo trạng thái
        if filter_status:
            domains.append([('house_status', '=', filter_status)])
        
        # Filter theo diện tích
        if filter_area_min:
            try:
                domains.append([('area', '>=', float(filter_area_min))])
            except (ValueError, TypeError):
                pass
        if filter_area_max:
            try:
                domains.append([('area', '<=', float(filter_area_max))])
            except (ValueError, TypeError):
                pass
        
        # Filter theo giá (nếu chưa có trong options)
        if filter_price_min and not options.get('min_price'):
            try:
                domains.append([('list_price', '>=', float(filter_price_min))])
            except (ValueError, TypeError):
                pass
        if filter_price_max and not options.get('max_price'):
            try:
                domains.append([('list_price', '<=', float(filter_price_max))])
            except (ValueError, TypeError):
                pass
        
        # Cập nhật base_domain
        result['base_domain'] = domains
        
        return result


