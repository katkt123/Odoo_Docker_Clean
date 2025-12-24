from odoo import models, fields, api

class PropertyType(models.Model):
    _name = 'smileliving.type'
    _description = 'Loại Bất Động Sản'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên Loại Bất Động Sản', required=True, tracking=True, help="Tên của loại bất động sản")
    description = fields.Text(string='Mô Tả', help="Mô tả loại bất động sản và các tiện ích đi kèm")
    amenity_ids = fields.Many2many('smileliving.amenity', string='Tiện Ích', help="Các tiện ích bao gồm trong loại bất động sản này")
    active = fields.Boolean(string='Hoạt Động', default=True)
    property_count = fields.Integer(string='Số Bất Động Sản', compute='_compute_property_count', store=True)

    @api.depends('name')
    def _compute_property_count(self):
        for record in self:
            record.property_count = self.env['smileliving.property'].search_count([
                ('type_id', '=', record.id)
            ])

    def action_view_properties(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bất Động Sản',
            'res_model': 'smileliving.property',
            'view_mode': 'list,form',
            'domain': [('type_id', '=', self.id)],
            'context': {'default_type_id': self.id},
        }

    def action_view_amenities(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tiện Ích',
            'res_model': 'smileliving.amenity',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.amenity_ids.ids)],
        }


class Amenity(models.Model):
    _name = 'smileliving.amenity'
    _description = 'Tiện Ích'

    name = fields.Char(string='Tên Tiện Ích', required=True, help="Tên của tiện ích")
    description = fields.Text(string='Mô Tả', help="Mô tả chi tiết về tiện ích")
    icon = fields.Char(string='Biểu Tượng', help="Biểu tượng đại diện cho tiện ích")
    active = fields.Boolean(string='Hoạt Động', default=True)
    property_type_count = fields.Integer(string='Số Loại BĐS', compute='_compute_property_type_count', store=True)

    @api.depends('name')
    def _compute_property_type_count(self):
        for record in self:
            record.property_type_count = self.env['smileliving.type'].search_count([('amenity_ids', '=', record.id)])

    def action_view_property_types(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loại Bất Động Sản',
            'res_model': 'smileliving.type',
            'view_mode': 'list,form',
            'domain': [('amenity_ids', '=', self.id)],
        }
