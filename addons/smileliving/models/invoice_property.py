from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class InvoiceProperty(models.Model):
    _name = 'smileliving.invoice'
    _description = 'Hóa Đơn Bất Động Sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    property_id = fields.Many2one(
        'smileliving.property',
        string='Bất Động Sản',
        required=True,
    )
    amount = fields.Monetary(string='Số Tiền', required=True)
    date = fields.Date(string='Ngày Lập Hóa Đơn', default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='Trạng Thái', default='draft', required=True)
    currency_id = fields.Many2one('res.currency', string='Tiền Tệ', default=lambda self: self.env.company.currency_id)
    partner_id = fields.Many2one('res.partner', string='Khách Hàng')
    description = fields.Text(string="Mô Tả")  # <-- Thêm dòng này
    
    def action_paid(self):
        """Mark invoice as paid"""
        if self.state != 'cancel':
            self.state = 'paid'
            self.message_post(body=_("Hóa đơn đã được đánh dấu là đã thanh toán"))

    def action_cancel(self):
        """Cancel the invoice"""
        if self.state == 'paid':
            raise UserError(_("Không thể hủy hóa đơn đã thanh toán"))
        self.state = 'cancel'
        self.message_post(body=_("Hóa đơn đã bị hủy"))

    def action_draft(self):
        """Reset invoice to draft state"""
        if self.state == 'paid':
            raise UserError(_("Không thể đặt lại hóa đơn đã thanh toán về bản nháp"))
        self.state = 'draft'
        self.message_post(body=_("Hóa đơn đã được đặt lại về bản nháp"))
