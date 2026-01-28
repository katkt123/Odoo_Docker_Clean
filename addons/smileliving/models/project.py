# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SmileLivingProject(models.Model):
    _name = 'smileliving.project'
    _description = 'Dự án (SmileLiving)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, id'

    name = fields.Char(string='Tên dự án', required=True, index=True)
    code = fields.Char(string='Mã dự án', index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company, required=True)

    developer_id = fields.Many2one(
        'res.partner',
        string='Chủ đầu tư',
        domain="['|', ('is_company', '=', True), ('parent_id', '=', False)]",
        tracking=True,
    )

    status = fields.Selection(
        [
            ('planning', 'Đang lập kế hoạch'),
            ('building', 'Đang xây dựng'),
            ('launch', 'Mở bán'),
            ('soldout', 'Đã bán hết'),
        ],
        string='Trạng thái dự án',
        default='planning',
        tracking=True,
    )

    start_date = fields.Date(string='Ngày khởi công', tracking=True)
    handover_date = fields.Date(string='Dự kiến bàn giao', tracking=True)

    address = fields.Char(string='Địa chỉ', tracking=True)
    tinhthanh_id = fields.Many2one('tinh.thanh', string='Tỉnh/Thành phố', tracking=True)
    quanhuyen_id = fields.Many2one('quan.huyen', string='Quận/Huyện', tracking=True)
    phuongxa_id = fields.Many2one('phuong.xa', string='Phường/Xã', tracking=True)

    description_short = fields.Char(string='Tóm tắt ngắn', tracking=True)
    description = fields.Html(string='Mô tả chi tiết')

    amenity_ids = fields.Many2many(
        'smileliving.amenity',
        'smileliving_project_amenity_rel',
        'project_id',
        'amenity_id',
        string='Tiện ích dự án',
        tracking=True,
    )

    property_ids = fields.One2many('smileliving.property', 'project_id', string='Các căn thuộc dự án')

    property_count = fields.Integer(compute='_compute_property_stats', string='Số căn')
    available_property_count = fields.Integer(compute='_compute_property_stats', string='Căn còn trống')
    reserved_property_count = fields.Integer(compute='_compute_property_stats', string='Căn đã giữ')
    sold_property_count = fields.Integer(compute='_compute_property_stats', string='Căn đã bán')

    planned_unit_count = fields.Integer(
        string='Số căn dự kiến',
        help='Tổng số căn của dự án (kế hoạch cố định do chủ đầu tư cung cấp).',
        tracking=True,
    )

    progress_percent = fields.Float(string='Tiến độ (%)', digits=(5, 2), help='Tiến độ thi công hoặc mở bán 0-100')

    hotline = fields.Char(string='Hotline dự án')
    website_url = fields.Char(string='Trang thông tin dự án')

    image_1920 = fields.Image(string='Ảnh dự án')
    image_1024 = fields.Image(related='image_1920', store=True, readonly=False)
    image_512 = fields.Image(related='image_1920', store=True, readonly=False)
    image_256 = fields.Image(related='image_1920', store=True, readonly=False)
    image_128 = fields.Image(related='image_1920', store=True, readonly=False)

    @api.depends('property_ids.house_status')
    def _compute_property_stats(self):
        for project in self:
            props = project.property_ids
            project.property_count = len(props)
            project.available_property_count = len(props.filtered(lambda p: p.house_status == 'available'))
            project.reserved_property_count = len(props.filtered(lambda p: p.house_status == 'reserved'))
            project.sold_property_count = len(props.filtered(lambda p: p.house_status == 'sold'))

    def action_open_properties(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Căn thuộc dự án',
            'res_model': 'smileliving.property',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
