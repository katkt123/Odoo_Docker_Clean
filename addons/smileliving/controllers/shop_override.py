from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleOverride(WebsiteSale):
    """Override shop controller to enforce a maximum products-per-page (ppg).

    This prevents clients from requesting an arbitrarily large `ppg` via URL
    params (e.g. `?ppg=999`) which can cause performance issues.
    """

    def shop(self, *args, **kwargs):
        try:
            ppg_param = request.params.get('ppg')
            ppg = int(ppg_param) if ppg_param is not None else int(kwargs.get('ppg') or 0)
        except Exception:
            ppg = 0

        MAX_PPG = 12
        if ppg > 0:
            capped = min(ppg, MAX_PPG)
            request.params['ppg'] = str(capped)
            kwargs['ppg'] = capped

        return super().shop(*args, **kwargs)
