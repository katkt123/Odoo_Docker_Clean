from odoo import models, fields, api

class EstateFinancialReport(models.Model):
    _name = 'estate.financial.report'
    _description = 'Báo cáo tài chính Bất động sản'
    _order = 'date desc'
    
    name = fields.Char('Tên báo cáo', required=True)
    date = fields.Date('Ngày báo cáo', required=True, default=fields.Date.today())
    period_type = fields.Selection([
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần'),
        ('monthly', 'Hàng tháng'),
        ('yearly', 'Hàng năm')
    ], string='Loại kỳ', required=True, default='daily')
    total_revenue = fields.Float('Tổng doanh thu', compute='_compute_total_revenue', store=True)
    total_expense = fields.Float('Tổng chi phí', compute='_compute_total_expense', store=True)
    net_profit = fields.Float('Lợi nhuận ròng', compute='_compute_net_profit', store=True)
    revenue_ids = fields.One2many('estate.revenue', 'report_id', string='Doanh thu')
    expense_ids = fields.One2many('estate.expense', 'report_id', string='Chi phí')
    property_ids = fields.Many2many('estate.property', string='Bất động sản')
    
    @api.depends('revenue_ids.amount')
    def _compute_total_revenue(self):
        for report in self:
            report.total_revenue = sum(report.revenue_ids.mapped('amount'))
    
    @api.depends('expense_ids.amount')
    def _compute_total_expense(self):
        for report in self:
            report.total_expense = sum(report.expense_ids.mapped('amount'))
    
    @api.depends('total_revenue', 'total_expense')
    def _compute_net_profit(self):
        for report in self:
            report.net_profit = report.total_revenue - report.total_expense
    
    @api.model
    def create_monthly_report(self, year, month):
        """Tạo báo cáo tháng"""
        domain = [
            ('date', '>=', f'{year}-{month:02d}-01'),
            ('date', '<=', f'{year}-{month:02d}-31')
        ]
        
        revenues = self.env['estate.revenue'].search(domain)
        expenses = self.env['estate.expense'].search(domain)
        
        report = self.create({
            'name': f'Báo cáo tháng {month}/{year}',
            'date': f'{year}-{month:02d}-01',
            'period_type': 'monthly',
            'revenue_ids': [(6, 0, revenues.ids)],
            'expense_ids': [(6, 0, expenses.ids)],
            'property_ids': [(6, 0, list(set(revenues.mapped('property_id').ids + expenses.mapped('property_id').ids)))]
        })
        
        return report
