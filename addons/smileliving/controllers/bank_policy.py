from odoo import http
from odoo.http import request


class SmileLivingBankPolicy(http.Controller):
    @http.route("/smileliving/bank-policy", type="http", auth="public", website=True, sitemap=True)
    def bank_policy(self, **kwargs):
        return request.render("smileliving.bank_policy_page")
