{
    'name': "Estate",
    'version': '1.0',
    'depends': ['base', 'mail', 'website', 'account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/estate_menu.xml',
        'views/estate_property_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_offer_views.xml',
        'views/estate_property_deposit_views.xml',
        'views/estate_invoice_views.xml',
        'views/estate_financial_report_views.xml',
        'views/estate_revenue_views.xml',
        'views/estate_expense_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate/static/src/js/sweet_alert.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}