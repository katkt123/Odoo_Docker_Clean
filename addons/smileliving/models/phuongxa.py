# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PhuongXa(models.Model):
    _name = 'phuong.xa'
    _description = 'Phường/Xã'
    _order = 'name'
    
    name = fields.Char('Tên phường/xã', required=True)
    code = fields.Char('Mã phường/xã', size=15, required=True)
    quanhuyen_id = fields.Many2one('quan.huyen', string='Quận/Huyện', required=True, ondelete='cascade')
    active = fields.Boolean('Hoạt động', default=True)

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            if not rec.code:
                continue
            dup = self.search([('id', '!=', rec.id), ('code', '=', rec.code)], limit=1)
            if dup:
                raise ValidationError('Mã phường/xã phải là duy nhất!')

    @api.constrains('name', 'quanhuyen_id')
    def _check_unique_name_in_quan(self):
        for rec in self:
            if not rec.name or not rec.quanhuyen_id:
                continue
            dup = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name),
                ('quanhuyen_id', '=', rec.quanhuyen_id.id),
            ], limit=1)
            if dup:
                raise ValidationError('Tên phường/xã phải là duy nhất trong cùng quận/huyện!')
