# estate_property.py
from odoo import models, fields, api

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Thông tin Bất Động Sản"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']

    # --- Cơ bản ---
    name = fields.Char("Tên BĐS", required=True)
    description = fields.Text("Mô tả")
    property_type_id = fields.Many2one("estate.property.type", string="Loại BĐS")
    tag_ids = fields.Many2many("estate.property.tag", string="Tiện ích")
    
    # --- Giá & Trạng thái ---
    expected_price = fields.Float("Giá mong muốn", required=True)
    selling_price = fields.Float("Giá bán chốt", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Tiền tệ")
    state = fields.Selection([
        ('new', 'Mới'),
        ('sold', 'Đã bán'),
        ('canceled', 'Đã hủy'),
    ], default='new', tracking=True)

    # --- Quan hệ (Kết nối với các file khác) ---
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Danh sách Đề nghị")
    deposit_ids = fields.One2many("estate.property.deposit", "property_id", string="Danh sách Đặt cọc")
    invoice_ids = fields.One2many("estate.invoice", "property_id", string="Lịch sử Hóa đơn")

    # --- Người phụ trách ---
    salesperson_id = fields.Many2one('res.users', default=lambda self: self.env.user, string="Salesman")
    buyer_id = fields.Many2one('res.partner', string="Người mua", copy=False)
    
    # --- Tài chính ---
    revenue_ids = fields.One2many('estate.revenue', 'property_id', string='Doanh thu')
    expense_ids = fields.One2many('estate.expense', 'property_id', string='Chi phí')
    total_revenue = fields.Float('Tổng doanh thu', compute='_compute_financial_summary', store=True)
    total_expense = fields.Float('Tổng chi phí', compute='_compute_financial_summary', store=True)
    net_profit = fields.Float('Lợi nhuận', compute='_compute_financial_summary', store=True)
    
    @api.depends('revenue_ids.amount', 'expense_ids.amount')
    def _compute_financial_summary(self):
        for prop in self:
            prop.total_revenue = sum(prop.revenue_ids.mapped('amount'))
            prop.total_expense = sum(prop.expense_ids.mapped('amount'))
            prop.net_profit = prop.total_revenue - prop.total_expense
    
    def action_create_revenue_from_sale(self):
        """Tạo doanh thu khi bán BĐS"""
        if self.state == 'sold' and self.selling_price > 0:
            self.env['estate.revenue'].create_from_property_sale(self.id, self.selling_price)
    
    def write(self, vals):
        """Ghi đè để tự động tạo doanh thu khi bán BĐS"""
        result = super(EstateProperty, self).write(vals)
        if vals.get('state') == 'sold':
            self.action_create_revenue_from_sale()
        return result