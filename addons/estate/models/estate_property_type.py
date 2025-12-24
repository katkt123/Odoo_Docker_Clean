# estate_property_type.py
from odoo import models, fields

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Loại Bất Động Sản"
    _order = "sequence, name"

    name = fields.Char("Tên loại", required=True)
    sequence = fields.Integer("Thứ tự", default=10)
    property_ids = fields.One2many("estate.property", "property_type_id", string="Bất động sản")

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Thẻ/Tiện ích Bất Động Sản"
    _order = "name"

    name = fields.Char("Tên thẻ", required=True)
    color = fields.Integer("Màu sắc")