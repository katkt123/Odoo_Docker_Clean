# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class TinhThanh(models.Model):
    _name = 'tinh.thanh'
    _description = 'Tỉnh/Thành phố'
    _order = 'name'
    
    name = fields.Char('Tên tỉnh/thành', required=True)
    code = fields.Char('Mã tỉnh/thành', size=5, required=True)
    active = fields.Boolean('Hoạt động', default=True)
    
    # Quan hệ với quận/huyện
    quanhuyen_ids = fields.One2many('quan.huyen', 'tinhthanh_id', string='Quận/Huyện')

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            if not rec.code:
                continue
            dup = self.search([('id', '!=', rec.id), ('code', '=', rec.code)], limit=1)
            if dup:
                raise ValidationError('Mã tỉnh/thành phải là duy nhất!')

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if not rec.name:
                continue
            dup = self.search([('id', '!=', rec.id), ('name', '=', rec.name)], limit=1)
            if dup:
                raise ValidationError('Tên tỉnh/thành phải là duy nhất!')
