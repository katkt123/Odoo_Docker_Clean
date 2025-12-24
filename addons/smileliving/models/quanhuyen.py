# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class QuanHuyen(models.Model):
    _name = 'quan.huyen'
    _description = 'Quận/Huyện'
    _order = 'name'
    
    name = fields.Char('Tên quận/huyện', required=True)
    code = fields.Char('Mã quận/huyện', size=10, required=True)
    tinhthanh_id = fields.Many2one('tinh.thanh', string='Tỉnh/Thành', required=True, ondelete='cascade')
    active = fields.Boolean('Hoạt động', default=True)
    
    # Quan hệ với phường/xã
    phuongxa_ids = fields.One2many('phuong.xa', 'quanhuyen_id', string='Phường/Xã')

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            if not rec.code:
                continue
            dup = self.search([('id', '!=', rec.id), ('code', '=', rec.code)], limit=1)
            if dup:
                raise ValidationError('Mã quận/huyện phải là duy nhất!')

    @api.constrains('name', 'tinhthanh_id')
    def _check_unique_name_in_tinh(self):
        for rec in self:
            if not rec.name or not rec.tinhthanh_id:
                continue
            dup = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name),
                ('tinhthanh_id', '=', rec.tinhthanh_id.id),
            ], limit=1)
            if dup:
                raise ValidationError('Tên quận/huyện phải là duy nhất trong cùng tỉnh/thành!')
