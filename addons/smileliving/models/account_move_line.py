# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    smileliving_is_smileliving = fields.Boolean(
        string="SmileLiving",
        compute="_compute_smileliving_is_smileliving",
        store=True,
        index=True,
        help="Checked when this journal item belongs to SmileLiving (based on analytic distribution).",
    )

    @api.depends("analytic_distribution", "company_id")
    def _compute_smileliving_is_smileliving(self):
        lines_by_company = {}
        for line in self:
            lines_by_company.setdefault(line.company_id, self.env["account.move.line"])
            lines_by_company[line.company_id] |= line

        for company, lines in lines_by_company.items():
            aa = (
                self.with_company(company)
                .env["sale.order.line"]
                ._smileliving_get_default_analytic_account()
            )
            aa_id = aa.id if aa else False
            aa_key = str(aa_id) if aa_id else None

            for line in lines:
                dist = line.analytic_distribution or {}
                if not aa_id or not dist:
                    line.smileliving_is_smileliving = False
                else:
                    line.smileliving_is_smileliving = (
                        aa_key in dist or aa_id in dist
                    )
