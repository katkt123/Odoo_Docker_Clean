# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    smile_product_tmpl_id = fields.Many2one(
        "product.template",
        string="Bất động sản quan tâm",
        help="Sản phẩm/căn nhà mà khách hàng quan tâm từ website.",
    )
    smile_property_id = fields.Many2one(
        "smileliving.property",
        string="Bất động sản (Property)",
        help="Bản ghi property liên kết (nếu có).",
    )

    smile_product_image_128 = fields.Image(
        related="smile_product_tmpl_id.image_128",
        readonly=True,
    )

    smile_product_tmpl_dbid = fields.Integer(
        string="ID sản phẩm",
        compute="_compute_smile_ids",
        readonly=True,
    )
    smile_property_dbid = fields.Integer(
        string="ID property",
        compute="_compute_smile_ids",
        readonly=True,
    )

    @api.depends("smile_product_tmpl_id", "smile_property_id")
    def _compute_smile_ids(self):
        for lead in self:
            lead.smile_product_tmpl_dbid = lead.smile_product_tmpl_id.id or 0
            lead.smile_property_dbid = lead.smile_property_id.id or 0

    @api.onchange("smile_product_tmpl_id")
    def _onchange_smile_product_tmpl_id(self):
        for lead in self:
            if lead.smile_product_tmpl_id and not lead.expected_revenue:
                lead.expected_revenue = lead.smile_product_tmpl_id.list_price
