from odoo import models, fields, api, _
from odoo.exceptions import UserError

class EstateInvoice(models.Model):
    _name = "estate.invoice"
    _description = "Giao dịch Thanh toán BĐS"
    _inherit = ['mail.thread']

    name = fields.Char("Mã giao dịch", default=lambda self: _('New'), readonly=True)
    property_id = fields.Many2one("estate.property", string="Tên bất động sản", required=True)
    partner_id = fields.Many2one("res.partner", string="Tên khách hàng", required=True)
    
    description = fields.Char("Nội dung thanh toán")
    origin = fields.Char("Nguồn gốc (Mã cọc)")
    
    amount_total = fields.Monetary("Số tiền", required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id')
    
    type = fields.Selection([
        ('deposit', 'Tiền cọc'),
        ('installment', 'Thanh toán đợt'),
        ('liquidation', 'Thanh toán tất toán')
    ], string="Loại thanh toán", required=True)

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('posted', 'Đã ghi nhận'),
        ('paid', 'Đã thanh toán')
    ], default='draft', tracking=True, compute='_compute_state', store=True, readonly=False)

    move_id = fields.Many2one('account.move', string="Hóa đơn Odoo", readonly=True, tracking=True)

    @api.depends('move_id.payment_state')
    def _compute_state(self):
        for record in self:
            if record.move_id:
                if record.move_id.payment_state == 'paid':
                    record.state = 'paid'
                elif record.move_id.state == 'posted':
                    record.state = 'posted'

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('name', _('New')) == _('New'):
                    vals['name'] = self.env['ir.sequence'].next_by_code('estate.invoice') or _('New')
            return super().create(vals_list)
        else:
            if vals_list.get('name', _('New')) == _('New'):
                vals_list['name'] = self.env['ir.sequence'].next_by_code('estate.invoice') or _('New')
            return super().create(vals_list)

    def action_post_entry(self):
        """Tạo Hóa đơn (Customer Invoice) trong module Account"""
        for record in self:
            # Kiểm tra nếu đã có hóa đơn nào của bất động sản này đã thanh toán
            paid_invoice = self.env['estate.invoice'].search([
                ('property_id', '=', record.property_id.id),
                ('state', '=', 'paid'),
                ('id', '!=', record.id)  # Loại trừ bản ghi hiện tại
            ], limit=1)
            
            if paid_invoice:
                raise UserError(_('Không thể tạo hóa đơn mới vì đã có hóa đơn khác của bất động sản này đã được thanh toán.'))
            
            # Kiểm tra nếu đã có hóa đơn và đã thanh toán
            if record.move_id and record.move_id.payment_state == 'paid':
                raise UserError(_('Không thể tạo hóa đơn mới vì hóa đơn này đã được thanh toán.'))
            
            # Nếu đã có hóa đơn nhưng chưa thanh toán, sử dụng lại hóa đơn đó
            if record.move_id and record.move_id.state == 'posted':
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': record.move_id.id,
                    'view_mode': 'form',
                    'target': 'current',
                    'flags': {'mode': 'readonly'},  
                }
            
            
            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': record.partner_id.id,
                'partner_shipping_id': record.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'name': f"{record.description} - {record.property_id.name}",
                    'quantity': 1,
                    'price_unit': record.amount_total,
                    'account_id': record.partner_id.property_account_receivable_id.id,
                })],
            }
            move = self.env['account.move'].with_context(default_move_type='out_invoice').create(move_vals)
            record.move_id = move.id
            record.state = 'posted'
            
            # Mở form xem hóa đơn vừa tạo
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': move.id,
                'view_mode': 'form',
                'target': 'current',
                'flags': {'mode': 'readonly'},  # Chỉ cho phép xem
            }

    def action_create_liquidation(self):
        """Chuyển hóa đơn hiện tại thành hóa đơn kết toán (thanh toán tất toán)"""
        self.ensure_one()
        
        # Tính toán số tiền còn lại cần thanh toán
        property_price = self.property_id.selling_price if self.property_id.selling_price > 0 else self.property_id.expected_price
        
        # Tính tổng các hóa đơn đã thanh toán của BĐS này (trừ bản ghi hiện tại)
        paid_invoices = self.env['estate.invoice'].search([
            ('property_id', '=', self.property_id.id),
            ('state', '=', 'paid'),
            ('id', '!=', self.id)
        ])
        total_paid = sum(invoice.amount_total for invoice in paid_invoices)
        
        # Số tiền cần thanh toán còn lại (tổng giá - đã thanh toán - tiền cọc)
        remaining_amount = property_price - total_paid - self.amount_total
        
        # Cập nhật hóa đơn hiện tại thành hóa đơn kết toán
        self.write({
            'amount_total': remaining_amount,
            'description': f"Thanh toán tất toán - {self.property_id.name}",
            'type': 'liquidation',
            'origin': f"Kết toán từ hóa đơn cọc {self.name}"
        })
        
        # Cập nhật account.move hiện tại
        if self.move_id and self.move_id.invoice_line_ids:
            # Cập nhật các dòng trong account.move
            self.move_id.write({
                'invoice_line_ids': [(1, self.move_id.invoice_line_ids[0].id, {
                    'name': f"Thanh toán tất toán - {self.property_id.name}",
                    'quantity': 1,
                    'price_unit': remaining_amount,
                })],
            })
        else:
            # Tạo mới account.move nếu chưa có hoặc không có dòng nào
            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'partner_shipping_id': self.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'name': f"Thanh toán tất toán - {self.property_id.name}",
                    'quantity': 1,
                    'price_unit': remaining_amount,
                    'account_id': self.partner_id.property_account_receivable_id.id,
                })],
            }
            move = self.env['account.move'].with_context(default_move_type='out_invoice').create(move_vals)
            self.move_id = move.id
        
        self.state = 'posted'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công!',
                'message': f'Đã chuyển thành hóa đơn kết toán: {remaining_amount:,.0f}',
                'type': 'success',
                'sticky': False,
            }
        }