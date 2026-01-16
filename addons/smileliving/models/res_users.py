from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _smileliving_website_company_ids(self):
        websites = self.env["website"].sudo().search([])
        return websites.mapped("company_id").ids

    def _smileliving_ensure_website_companies(self):
        website_company_ids = self._smileliving_website_company_ids()
        if not website_company_ids:
            return

        for user in self:
            if not user.share:
                continue

            missing_company_ids = set(website_company_ids) - set(user.company_ids.ids)
            if not missing_company_ids:
                continue

            user.sudo().with_context(smileliving_skip_company_fix=True).write(
                {"company_ids": [(4, company_id) for company_id in sorted(missing_company_ids)]}
            )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if not self.env.context.get("smileliving_skip_company_fix"):
            users._smileliving_ensure_website_companies()
        return users

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("smileliving_skip_company_fix"):
            return res

        # Only run the fix when something relevant may have changed.
        if {"share", "company_ids", "company_id", "group_ids"}.intersection(vals.keys()):
            self._smileliving_ensure_website_companies()

        return res
