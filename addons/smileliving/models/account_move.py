# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    smileliving_is_smileliving = fields.Boolean(
        string="SmileLiving",
        compute="_compute_smileliving_is_smileliving",
        store=True,
        index=True,
        help="Checked when this entry contains SmileLiving journal items.",
    )

    @api.depends("line_ids.smileliving_is_smileliving")
    def _compute_smileliving_is_smileliving(self):
        for move in self:
            move.smileliving_is_smileliving = any(
                line.smileliving_is_smileliving for line in move.line_ids
            )

    def write(self, vals):
        res = super().write(vals)

        # Business rule: once the sale invoice is fully paid, mark the related
        # property as sold and unpublish it from the website.
        if 'payment_state' not in vals and 'state' not in vals:
            return res

        moves = self.filtered(lambda m: m.move_type in ('out_invoice', 'out_receipt') and m.state == 'posted')
        moves = moves.filtered(lambda m: getattr(m, 'payment_state', False) == 'paid')
        if not moves:
            return res

        ProductTmpl = self.env['product.template']
        tmpl_ids = set()
        for move in moves:
            for line in move.invoice_line_ids:
                if line.product_id and line.product_id.product_tmpl_id:
                    tmpl_ids.add(line.product_id.product_tmpl_id.id)

        if not tmpl_ids:
            return res

        properties = self.env['smileliving.property'].search([('product_tmpl_id', 'in', list(tmpl_ids))])
        if properties:
            properties.write({
                'house_status': 'sold',
                'is_publish': False,
            })

        return res

