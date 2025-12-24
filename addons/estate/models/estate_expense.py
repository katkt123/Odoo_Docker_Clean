from odoo import models, fields, api

class EstateExpense(models.Model):
    _name = 'estate.expense'
    _description = 'Chi phí Bất động sản'
    _order = 'date desc'
    
    name = fields.Char('Mô tả', required=True)
    date = fields.Date('Ngày', required=True, default=fields.Date.today())
    amount = fields.Float('Số tiền', required=True)
    expense_type = fields.Selection([
        ('maintenance', 'Bảo trì'),
        ('utility', 'Tiện ích'),
        ('tax', 'Thuế'),
        ('insurance', 'Bảo hiểm'),
        ('commission', 'Hoa hồng'),
        ('marketing', 'Marketing'),
        ('legal', 'Pháp lý'),
        ('other', 'Khác')
    ], string='Loại chi phí', required=True)
    property_id = fields.Many2one('estate.property', string='Bất động sản')
    vendor_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    report_id = fields.Many2one('estate.financial.report', string='Báo cáo')
    bill_id = fields.Many2one('account.move', string='Hóa đơn')
    paid = fields.Boolean('Đã thanh toán', default=False)
    payment_date = fields.Date('Ngày thanh toán')
    
    @api.model
    def create(self, vals):
        # Tự động gán vào báo cáo tương ứng
        if vals.get('date'):
            report = self.env['estate.financial.report'].search([
                ('date', '=', vals['date']),
                ('period_type', '=', 'daily')
            ], limit=1)
            if not report:
                report = self.env['estate.financial.report'].create({
                    'name': f'Báo cáo {vals["date"]}',
                    'date': vals['date'],
                    'period_type': 'daily'
                })
            vals['report_id'] = report.id
        return super(EstateExpense, self).create(vals)
    
    def action_mark_paid(self):
        """Đánh dấu đã thanh toán"""
        self.paid = True
        self.payment_date = fields.Date.today()
    
    @api.model
    def create_commission_expense(self, property_id, commission_amount):
        """Tạo chi phí hoa hồng"""
        property_record = self.env['estate.property'].browse(property_id)
        if property_record.exists():
            self.create({
                'name': f'Hoa hồng bán BĐS: {property_record.name}',
                'date': fields.Date.today(),
                'amount': commission_amount,
                'expense_type': 'commission',
                'property_id': property_id,
                'vendor_id': property_record.salesperson_id.partner_id.id if property_record.salesperson_id.partner_id else None
            })
