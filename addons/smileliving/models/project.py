# -*- coding: utf-8 -*-

from odoo import fields, models


class SmileLivingProject(models.Model):
    _name = 'smileliving.project'
    _description = 'Dự án (SmileLiving)'
    _order = 'name, id'

    name = fields.Char(string='Tên dự án', required=True, index=True)
    code = fields.Char(string='Mã dự án', index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.company, required=True)
