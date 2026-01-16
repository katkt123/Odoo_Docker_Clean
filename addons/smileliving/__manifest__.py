{
    'name': "SmileLiving",
    'version': '1.0',
    'depends': ['base', 'mail', 'web', 'website', 'website_sale', 'website_sale_wishlist', 'crm', 'account'],
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_frontend': [
            'smileliving/static/src/interactions/area_range.js',
            'smileliving/static/src/css/project.css',
            'smileliving/static/src/css/website.css',
            'smileliving/static/src/js/livechat_product_action.js',
            'smileliving/static/src/scss/loan_policy.scss',
            'smileliving/static/src/js/loan_calculator.js',
        ],
        'web.assets_backend': [
            'smileliving/static/src/js/livechat_product_action.js',
        ],
        'im_livechat.assets_embed': [
            'smileliving/static/src/js/livechat_product_action.js',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/smileliving_seed_cron.xml',
        'views/house_property_views.xml',
        'views/smileliving_reporting_views.xml',
        'views/smileliving_project_views.xml',
        'views/property_type_views.xml',
        'views/crm_lead_interest_views.xml',
        'views/sale_order_interest_views.xml',
        'views/website_sale_interest_inherit.xml',
        'views/website_sale_wishlist_interest_inherit.xml',
        'views/smileliving_template_views.xml',
        'views/smileliving_login_views.xml',
        'views/product_item_inherit.xml',
        'views/wishlist_minimal_tile_inherit.xml',
        'views/website_bank_policy.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

