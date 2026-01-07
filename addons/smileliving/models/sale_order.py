# -*- coding: utf-8 -*-

from odoo import Command, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    smile_product_tmpl_id = fields.Many2one(
        "product.template",
        related="opportunity_id.smile_product_tmpl_id",
        readonly=True,
    )
    smile_property_id = fields.Many2one(
        "smileliving.property",
        related="opportunity_id.smile_property_id",
        readonly=True,
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
        for order in self:
            order.smile_product_tmpl_dbid = order.smile_product_tmpl_id.id or 0
            order.smile_property_dbid = order.smile_property_id.id or 0

    def _smileliving_prepare_interest_line_vals(self, tmpl):
        self.ensure_one()
        product = tmpl.product_variant_id
        if not product:
            return False

        line = self.env['sale.order.line'].new({
            'order_id': self,
            'product_id': product.id,
            'product_uom_qty': 1.0,
        })
        if hasattr(line, '_onchange_product_id'):
            line._onchange_product_id()
        if hasattr(line, '_onchange_product_uom_qty'):
            line._onchange_product_uom_qty()

        vals = line._convert_to_write(line._cache)
        vals.pop('order_id', None)
        vals.pop('order_partner_id', None)
        return vals

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        if 'order_line' not in fields_list or defaults.get('order_line'):
            return defaults

        ctx = self.env.context
        opportunity_id = ctx.get('default_opportunity_id')
        if not opportunity_id and ctx.get('active_model') == 'crm.lead' and ctx.get('active_id'):
            opportunity_id = ctx.get('active_id')

        if not opportunity_id:
            return defaults

        opportunity = self.env['crm.lead'].browse(opportunity_id).exists()
        if not opportunity or not opportunity.smile_product_tmpl_id:
            return defaults

        order = self.new(defaults)
        vals = order._smileliving_prepare_interest_line_vals(opportunity.smile_product_tmpl_id)
        if vals:
            defaults['order_line'] = [Command.create(vals)]

        return defaults

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id_smileliving_interest_line(self):
        for order in self:
            if order.order_line:
                continue
            if not order.opportunity_id or not order.opportunity_id.smile_product_tmpl_id:
                continue

            vals = order._smileliving_prepare_interest_line_vals(order.opportunity_id.smile_product_tmpl_id)
            if vals:
                order.order_line = [Command.create(vals)]

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)

        for order in orders:
            if order.order_line:
                continue
            opportunity = order.opportunity_id
            if not opportunity or not opportunity.smile_product_tmpl_id:
                continue

            vals = order._smileliving_prepare_interest_line_vals(opportunity.smile_product_tmpl_id)
            if vals:
                order.write({'order_line': [Command.create(vals)]})

        return orders

    def action_confirm(self):
        res = super().action_confirm()

        # Business rule: once the contract is confirmed, the property should no
        # longer be visible on the website.
        self._smileliving_on_contract_confirm()

        return res

    def _smileliving_on_contract_confirm(self):
        Property = self.env['smileliving.property'].sudo()
        templates = self.mapped('order_line.product_id.product_tmpl_id').filtered(lambda t: t)
        if not templates:
            return

        props = Property.search([('product_tmpl_id', 'in', templates.ids)])
        for prop in props:
            vals = {'is_publish': False}
            if prop.house_status == 'available':
                vals['house_status'] = 'reserved'
            prop.write(vals)
