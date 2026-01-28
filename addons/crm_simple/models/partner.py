from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    lead_ids = fields.One2many('crm.lead', 'partner_id', string='Leads')
    x_is_guest = fields.Boolean(string='Is Guest', compute='_compute_is_guest')

    def _compute_is_guest(self):
        for rec in self:
            # Fallback rule: consider guest when customer_rank is falsy or partner has no sale orders
            try:
                customer_rank = getattr(rec, 'customer_rank', 0) or 0
            except Exception:
                customer_rank = 0
            rec.x_is_guest = (customer_rank == 0)
