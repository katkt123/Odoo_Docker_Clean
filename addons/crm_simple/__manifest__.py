{
    "name": "CRM Simple",
    "version": "19.0.1.0.0",
    "category": "CRM",
    "summary": "Simple CRM customization: add a couple of fields to Leads",
    "description": """
    CRM Simple
    ==========

    A minimal custom addon for Odoo 19 that extends CRM Leads with a few extra fields.

    Purpose
    -------
    - Provide a clean, uploadable example addon structure
    - Avoid shadowing Odoo's core `crm` addon (this module's technical name is `crm_simple`)
    """,
    "author": "HaoKiet",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "views/crm_lead_views.xml",
        "views/crm_simple_menu.xml",
        "data/demo_crm_demo.xml",
        "views/crm_simple_360.xml",
        "views/partner_360_button.xml",
    ],
    "installable": True,
    "application": True,
}
