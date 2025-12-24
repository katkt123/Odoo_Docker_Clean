from odoo import models, fields, api

class EstateRevenue(models.Model):
    _name = 'estate.revenue'
    _description = 'Doanh thu Bất động sản'
    _order = 'date desc'
    
    name = fields.Char('Mô tả', required=True)
    date = fields.Date('Ngày', required=True, default=fields.Date.today())
    amount = fields.Float('Số tiền', required=True)
    revenue_type = fields.Selection([
        ('rent', 'Thuê nhà'),
        ('sale', 'Bán nhà'),
        ('service', 'Dịch vụ'),
        ('deposit', 'Tiền cọc'),
        ('commission', 'Hoa hồng'),
        ('other', 'Khác')
    ], string='Loại doanh thu', required=True)
    property_id = fields.Many2one('estate.property', string='Bất động sản')
    customer_id = fields.Many2one('res.partner', string='Khách hàng')
    report_id = fields.Many2one('estate.financial.report', string='Báo cáo')
    estate_invoice_id = fields.Many2one('estate.invoice', string='Hóa đơn BĐS')
    payment_date = fields.Date('Ngày thanh toán')
    
    # Computed field để lấy hóa đơn đã thanh toán của BĐS
    paid_invoice_id = fields.Many2one('estate.invoice', string='Hóa đơn đã thanh toán', compute='_compute_paid_invoice')
    
    @api.depends('property_id')
    def _compute_paid_invoice(self):
        """Tự động lấy hóa đơn đã thanh toán của BĐS"""
        for record in self:
            if record.property_id:
                paid_invoice = record.env['estate.invoice'].search([
                    ('property_id', '=', record.property_id.id),
                    ('state', '=', 'paid')
                ], limit=1)
                record.paid_invoice_id = paid_invoice.id if paid_invoice else False
                # Nếu có hóa đơn đã thanh toán, tự động cập nhật các thông tin
                if paid_invoice and not record.estate_invoice_id:
                    record.estate_invoice_id = paid_invoice.id
                    record.customer_id = paid_invoice.partner_id.id
                    record.payment_date = paid_invoice.move_id.invoice_date if paid_invoice.move_id else fields.Date.today()
                    # Lấy số tiền từ giá bán của hóa đơn đã thanh toán
                    record.amount = paid_invoice.amount_total
                    # Gợi ý tên doanh thu dựa trên thông tin hóa đơn
                    record.name = f"Doanh thu từ {record.property_id.name} - {paid_invoice.name}"
            else:
                record.paid_invoice_id = False
    
    @api.model
    def create(self, vals):
        # Xử lý cả trường hợp vals là list hoặc dictionary
        if isinstance(vals, list):
            # Xử lý list
            for val in vals:
                if val.get('date'):
                    report = self.env['estate.financial.report'].search([
                        ('date', '=', val['date']),
                        ('period_type', '=', 'daily')
                    ], limit=1)
                    if not report:
                        report = self.env['estate.financial.report'].create({
                            'name': f'Báo cáo {val["date"]}',
                            'date': val['date'],
                            'period_type': 'daily'
                        })
                    val['report_id'] = report.id
            return super(EstateRevenue, self).create(vals)
        else:
            # Xử lý single dictionary
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
            return super(EstateRevenue, self).create(vals)
    
    def action_mark_paid(self):
        """Đánh dấu đã thanh toán"""
        self.paid = True
        self.payment_date = fields.Date.today()
    
    @api.model
    def auto_create_revenue_from_paid_invoices(self):
        """Tự động tạo doanh thu từ tất cả các hóa đơn đã thanh toán chưa được ghi nhận"""
        # Lấy tất cả các hóa đơn đã thanh toán
        all_paid_invoices = self.env['estate.invoice'].search([('state', '=', 'paid')])
        
        revenues_created = []
        for invoice in all_paid_invoices:
            # Kiểm tra đã có doanh thu từ hóa đơn này chưa
            existing_revenue = self.search([('estate_invoice_id', '=', invoice.id)])
            if existing_revenue:
                continue  # Bỏ qua nếu đã có doanh thu từ hóa đơn này
            
            # Xác định loại doanh thu theo loại hóa đơn
            revenue_type = 'sale'  # Mặc định
            if invoice.type == 'deposit':
                revenue_type = 'deposit'
            elif invoice.type == 'installment':
                revenue_type = 'sale'
            elif invoice.type == 'liquidation':
                revenue_type = 'sale'
            
            # Tạo doanh thu từ hóa đơn - chỉ cần các trường cơ bản
            revenue_vals = {
                'name': f'Doanh thu tự động: {invoice.description or "Hóa đơn BĐS"}',
                'date': invoice.move_id.invoice_date if invoice.move_id else fields.Date.today(),
                'revenue_type': revenue_type,
                'amount': invoice.amount_total,
                'payment_date': invoice.move_id.invoice_date if invoice.move_id else fields.Date.today(),
                'estate_invoice_id': invoice.id,
            }
            
            # Chỉ thêm các trường optional nếu có dữ liệu
            if invoice.property_id:
                revenue_vals['property_id'] = invoice.property_id.id
            if invoice.partner_id:
                revenue_vals['customer_id'] = invoice.partner_id.id
            
            # Tạo doanh thu với context bỏ qua validation
            revenue = self.with_context(skip_required_validation=True).create(revenue_vals)
            revenues_created.append(revenue.id)
        
        return revenues_created
    
    def action_sync_paid_invoices(self):
        """Đồng bộ doanh thu từ các hóa đơn đã thanh toán"""
        created_revenues = self.auto_create_revenue_from_paid_invoices()
        
        if created_revenues:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công!',
                    'message': f'Đã tạo {len(created_revenues)} khoản doanh thu từ hóa đơn đã thanh toán.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Không có hóa đơn đã thanh toán mới để đồng bộ.',
                    'type': 'info',
                    'sticky': False,
                }
            }
        
    @api.model
    def create_from_property_sale(self, property_id, selling_price):
        """Tạo doanh thu từ bán bất động sản"""
        property_record = self.env['estate.property'].browse(property_id)
        if property_record.exists():
            self.create({
                'name': f'Bán bất động sản: {property_record.name}',
                'date': fields.Date.today(),
                'amount': selling_price,
                'revenue_type': 'sale',
                'property_id': property_id,
                'customer_id': property_record.buyer_id.id if property_record.buyer_id else None,
                'paid': True,
                'payment_date': fields.Date.today()
            })

    
