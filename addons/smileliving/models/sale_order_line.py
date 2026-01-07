# -*- coding: utf-8 -*-

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def _smileliving_get_default_analytic_plan(self):
        """Return (and create if needed) an Analytic Plan for SmileLiving.

        In Odoo 17+, analytic accounts must belong to an analytic plan
        (`plan_id` is mandatory). This helper guarantees we always have one.
        """
        company = self.env.company
        ICP = self.env["ir.config_parameter"].sudo()
        key = f"smileliving.analytic_plan_id.{company.id}"
        existing_id = ICP.get_param(key)

        try:
            Plan = self.env["account.analytic.plan"].sudo()
        except KeyError:
            return False

        if existing_id:
            plan = Plan.browse(int(existing_id)).exists()
            if plan:
                return plan

        domain = [("name", "=", "SmileLiving")]
        if "company_id" in Plan._fields:
            domain.append(("company_id", "=", company.id))

        plan = Plan.search(domain, limit=1)
        if not plan:
            vals = {"name": "SmileLiving"}
            if "company_id" in Plan._fields:
                vals["company_id"] = company.id
            plan = Plan.create(vals)

        ICP.set_param(key, str(plan.id))
        return plan

    @api.model
    def _smileliving_get_default_analytic_account(self):
        """Return the default analytic account for SmileLiving.

        We use this to tag SmileLiving lines so Accounting reports can be
        filtered to only SmileLiving activity.
        """
        company = self.env.company
        ICP = self.env["ir.config_parameter"].sudo()
        key = f"smileliving.analytic_account_id.{company.id}"
        existing_id = ICP.get_param(key)

        Analytic = self.env["account.analytic.account"].sudo()

        plan = self._smileliving_get_default_analytic_plan()

        if existing_id:
            aa = Analytic.browse(int(existing_id)).exists()
            if aa:
                if plan and not aa.plan_id:
                    aa.write({"plan_id": plan.id})
                return aa

        aa = Analytic.search([
            ("name", "=", "SmileLiving"),
            ("company_id", "=", company.id),
        ], limit=1)
        if not aa:
            vals = {
                "name": "SmileLiving",
                "company_id": company.id,
            }
            if plan and "plan_id" in Analytic._fields:
                vals["plan_id"] = plan.id
            aa = Analytic.create(vals)
        elif plan and not aa.plan_id:
            aa.write({"plan_id": plan.id})

        ICP.set_param(key, str(aa.id))
        return aa

    @api.model
    def _smileliving_templates_to_tag(self, template_ids):
        if not template_ids:
            return set()
        props = self.env["smileliving.property"].sudo().search([
            ("product_tmpl_id", "in", list(template_ids)),
        ])
        return set(props.mapped("product_tmpl_id").ids)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._smileliving_apply_analytic_tag_if_needed()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self._smileliving_apply_analytic_tag_if_needed()
        return res

    def _smileliving_apply_analytic_tag_if_needed(self):
        # Only set analytic_distribution when empty, to avoid overwriting user rules.
        candidates = self.filtered(lambda l: not l.analytic_distribution and not getattr(l, "is_downpayment", False))
        if not candidates:
            return

        template_ids = {l.product_id.product_tmpl_id.id for l in candidates if l.product_id and l.product_id.product_tmpl_id}
        smile_tmpl_ids = self._smileliving_templates_to_tag(template_ids)
        if not smile_tmpl_ids:
            return

        aa = self._smileliving_get_default_analytic_account()
        dist = {str(aa.id): 100}

        to_tag = candidates.filtered(lambda l: l.product_id and l.product_id.product_tmpl_id.id in smile_tmpl_ids)
        if to_tag:
            to_tag.sudo().write({"analytic_distribution": dist})
