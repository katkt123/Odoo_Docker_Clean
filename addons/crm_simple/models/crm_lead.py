from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_hk_ref = fields.Char(string="HK Reference")
    x_hk_note = fields.Text(string="HK Note")
