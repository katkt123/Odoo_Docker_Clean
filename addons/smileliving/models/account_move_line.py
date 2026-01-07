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

    smileliving_property_id = fields.Many2one(
        'smileliving.property',
        string='Căn (SmileLiving)',
        compute='_compute_smileliving_property_project',
        store=True,
        index=True,
    )

    smileliving_project_id = fields.Many2one(
        'smileliving.project',
        string='Dự án (SmileLiving)',
        compute='_compute_smileliving_property_project',
        store=True,
        index=True,
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

    @api.depends('product_id', 'product_id.product_tmpl_id')
    def _compute_smileliving_property_project(self):
        template_ids = set()
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id:
                template_ids.add(line.product_id.product_tmpl_id.id)

        prop_by_tmpl = {}
        if template_ids:
            props = self.env['smileliving.property'].sudo().search([
                ('product_tmpl_id', 'in', list(template_ids)),
            ])
            prop_by_tmpl = {p.product_tmpl_id.id: p for p in props}

        for line in self:
            prop = False
            if line.product_id and line.product_id.product_tmpl_id:
                prop = prop_by_tmpl.get(line.product_id.product_tmpl_id.id)

            line.smileliving_property_id = prop.id if prop else False
            line.smileliving_project_id = prop.project_id.id if prop and prop.project_id else False
