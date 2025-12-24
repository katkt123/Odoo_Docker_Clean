from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class EstatePropertyDeposit(models.Model):
    _name = "estate.property.deposit"
    _description = "Phiếu Đặt Cọc / Giữ Chỗ"
    _inherit = ['mail.thread']

    name = fields.Char("Mã đặt cọc", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    property_id = fields.Many2one("estate.property", string ="Tên bất động sản", required=True)
    partner_id = fields.Many2one("res.partner", string="Khách hàng", required=True)
    
    amount = fields.Monetary("Số tiền cọc", required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='property_id.currency_id')
    date_deposit = fields.Date("Ngày đặt", default=fields.Date.today())
    note = fields.Text("Ghi chú")
    
    # --- Trả góp ---
    installment_type = fields.Selection([
        ('none', 'Không trả góp'),
        ('monthly', 'Trả góp hàng tháng'),
        ('yearly', 'Trả góp hàng năm')
    ], string="Hình thức trả góp", default='none', required=True)
    
    installment_months = fields.Integer("Số tháng trả góp", 
                                       help="Tổng số tháng để hoàn tất thanh toán")
    installment_years = fields.Integer("Số năm trả góp", 
                                      help="Tổng số năm để hoàn tất thanh toán")
    monthly_payment = fields.Monetary("Tiền trả hàng tháng", 
                                     currency_field='currency_id',
                                     compute='_compute_installment_payment',
                                     store=True,
                                     help="Số tiền cần trả mỗi tháng")
    yearly_payment = fields.Monetary("Tiền trả hàng năm", 
                                    currency_field='currency_id',
                                    compute='_compute_installment_payment',
                                    store=True,
                                    help="Số tiền cần trả mỗi năm")
    total_installment_amount = fields.Monetary("Tổng tiền trả góp", 
                                              currency_field='currency_id',
                                              compute='_compute_installment_payment',
                                              store=True,
                                              help="Tổng số tiền cần trả góp")
    completion_date = fields.Date("Ngày hoàn tất thanh toán", 
                                  compute='_compute_completion_date',
                                  store=True,
                                  help="Ngày dự kiến hoàn tất thanh toán")

    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('cancel', 'Hủy')
    ], default='draft', tracking=True)

    @api.constrains('amount')
    def _check_deposit_amount(self):
        for record in self:
            if record.property_id:
                # Lấy giá giới hạn (selling_price nếu có, không thì expected_price)
                max_amount = record.property_id.selling_price if record.property_id.selling_price > 0 else record.property_id.expected_price
                
                if record.amount > max_amount:
                    raise ValidationError(f"Số tiền cọc ({record.amount}) không thể vượt quá giá BĐS ({max_amount})")

    @api.depends('amount', 'installment_type', 'installment_months', 'installment_years', 'property_id.expected_price', 'property_id.selling_price')
    def _compute_installment_payment(self):
        for record in self:
            # Reset values
            record.monthly_payment = 0.0
            record.yearly_payment = 0.0
            record.total_installment_amount = 0.0
            
            if record.installment_type == 'none':
                continue
            
            # Lấy giá BĐS để tính toán
            property_price = record.property_id.selling_price if record.property_id.selling_price > 0 else record.property_id.expected_price
            remaining_amount = property_price - record.amount
            
            if record.installment_type == 'monthly' and record.installment_months > 0:
                record.monthly_payment = remaining_amount / record.installment_months
                record.total_installment_amount = remaining_amount
            elif record.installment_type == 'yearly' and record.installment_years > 0:
                record.yearly_payment = remaining_amount / record.installment_years
                record.total_installment_amount = remaining_amount

    @api.depends('date_deposit', 'installment_type', 'installment_months', 'installment_years')
    def _compute_completion_date(self):
        for record in self:
            record.completion_date = False
            if record.date_deposit:
                if record.installment_type == 'monthly' and record.installment_months > 0:
                    # Cộng số tháng vào ngày đặt cọc
                    from datetime import timedelta, date
                    completion_date = fields.Date.from_string(record.date_deposit)
                    # Thêm số tháng (khoảng 30 ngày mỗi tháng)
                    completion_date = completion_date + timedelta(days=record.installment_months * 30)
                    record.completion_date = completion_date
                elif record.installment_type == 'yearly' and record.installment_years > 0:
                    # Cộng số năm vào ngày đặt cọc
                    from datetime import timedelta, date
                    completion_date = fields.Date.from_string(record.date_deposit)
                    # Thêm số năm (365 ngày mỗi năm)
                    completion_date = completion_date + timedelta(days=record.installment_years * 365)
                    record.completion_date = completion_date

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, list):
            # Xử lý trường hợp tạo nhiều bản ghi
            for vals in vals_list:
                if vals.get('name', _('New')) == _('New'):
                    vals['name'] = self.env['ir.sequence'].next_by_code('estate.property.deposit') or _('New')
            return super().create(vals_list)
        else:
            # Xử lý trường hợp tạo một bản ghi
            if vals_list.get('name', _('New')) == _('New'):
                vals_list['name'] = self.env['ir.sequence'].next_by_code('estate.property.deposit') or _('New')
            return super().create(vals_list)

    def action_confirm(self):
        """Xác nhận đặt cọc và chuyển thành hóa đơn"""
        self.ensure_one()
        
        # Tạo hóa đơn cọc với state posted
        invoice = self.env['estate.invoice'].create({
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'amount_total': self.amount,
            'description': f"Thanh toán tiền cọc: {self.name}",
            'type': 'deposit',
            'origin': self.name,
            'state': 'posted'  # Đặt state là posted ngay khi tạo
        })
        
        # Tự động tạo account.move cho hóa đơn cọc
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': [(0, 0, {
                'name': f"Thanh toán tiền cọc: {self.name}",
                'quantity': 1,
                'price_unit': self.amount,
                'account_id': self.partner_id.property_account_receivable_id.id,
            })],
        }
        move = self.env['account.move'].with_context(default_move_type='out_invoice').create(move_vals)
        invoice.move_id = move.id
        
        self.state = 'confirmed'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.invoice',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Hủy đặt cọc và chuyển BĐS về trạng thái mới"""
        self.ensure_one()
        self.state = 'cancel'
        
        # Chuyển trạng thái BĐS về "Mới"
        if self.property_id:
            self.property_id.state = 'new'
            self.property_id.buyer_id = False
            self.property_id.selling_price = 0
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đã hủy',
                'message': f'Phiếu đặt cọc {self.name} đã bị hủy',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_create_installment_invoices(self):
        """Tạo tất cả hóa đơn trả góp một lần"""
        self.ensure_one()
        
        if self.installment_type == 'none':
            raise UserError("Phiếu đặt cọc này không có kế hoạch trả góp")
        
        if not self.monthly_payment and not self.yearly_payment:
            raise UserError("Chưa tính toán số tiền trả góp")
        
        invoices = self.env['estate.invoice']
        
        if self.installment_type == 'monthly':
            # Tạo hóa đơn cho từng tháng
            for month in range(1, self.installment_months + 1):
                invoice = self.env['estate.invoice'].create({
                    'property_id': self.property_id.id,
                    'partner_id': self.partner_id.id,
                    'amount_total': self.monthly_payment,
                    'description': f"Thanh toán đợt {month}/{self.installment_months} - {self.name}",
                    'type': 'installment',
                    'origin': self.name
                })
                invoices |= invoice
                
        elif self.installment_type == 'yearly':
            # Tạo hóa đơn cho từng năm
            for year in range(1, self.installment_years + 1):
                invoice = self.env['estate.invoice'].create({
                    'property_id': self.property_id.id,
                    'partner_id': self.partner_id.id,
                    'amount_total': self.yearly_payment,
                    'description': f"Thanh toán năm {year}/{self.installment_years} - {self.name}",
                    'type': 'installment',
                    'origin': self.name
                })
                invoices |= invoice
        
        self.state = 'confirmed'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estate.invoice',
            'domain': [('id', 'in', invoices.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }