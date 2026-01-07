# -*- coding: utf-8 -*-

from odoo import Command, api, fields, models


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

    def _smileliving_autocreate_sale_order_on_won(self):
        """Create a quotation automatically when an opportunity becomes Won.

        This uses a simple, realistic default flow:
        - 1 property = 1 sale order line (qty=1)
        - price = product template list price

        We only do it when we have enough data to avoid creating junk docs.
        """
        SaleOrder = self.env['sale.order']

        for lead in self:
            if lead.type != 'opportunity':
                continue
            if not lead.partner_id:
                continue
            if not lead.smile_product_tmpl_id:
                continue

            existing = SaleOrder.search([
                ('opportunity_id', '=', lead.id),
            ], limit=1)
            if existing:
                continue

            product = lead.smile_product_tmpl_id.product_variant_id
            if not product:
                continue

            order_vals = {
                'partner_id': lead.partner_id.id,
                'opportunity_id': lead.id,
                'origin': lead.name,
            }
            order = SaleOrder.create(order_vals)

            # Use the helper from our sale.order extension so onchanges and
            # default taxes/uom/description are applied correctly.
            line_vals = order._smileliving_prepare_interest_line_vals(lead.smile_product_tmpl_id)
            if line_vals:
                order.write({'order_line': [Command.create(line_vals)]})

    def action_set_won(self):
        res = super().action_set_won()
        self._smileliving_autocreate_sale_order_on_won()
        return res

    def action_set_won_rainbowman(self):
        res = super().action_set_won_rainbowman()
        # `crm` calls `action_set_won()` from inside this method, so our
        # override on `action_set_won()` already handles the automation.
        return res
