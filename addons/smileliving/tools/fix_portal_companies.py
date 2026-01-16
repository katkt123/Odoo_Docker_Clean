from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry


def main(db_name: str = "odoo_clean") -> None:
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        website_company_ids = env["website"].sudo().search([]).mapped("company_id").ids
        portal_users = env["res.users"].sudo().search([("share", "=", True)])

        updated = 0
        for user in portal_users:
            missing = set(website_company_ids) - set(user.company_ids.ids)
            if not missing:
                continue
            user.with_context(smileliving_skip_company_fix=True).write(
                {"company_ids": [(4, company_id) for company_id in sorted(missing)]}
            )
            updated += 1

        print({
            "db": db_name,
            "website_company_ids": website_company_ids,
            "portal_users": len(portal_users),
            "updated_users": updated,
        })


if __name__ == "__main__":
    main()
