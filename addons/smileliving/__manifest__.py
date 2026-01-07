{
    'name': "SmileLiving",
    'version': '1.0',
    'depends': ['base', 'mail', 'web', 'website', 'website_sale', 'website_sale_wishlist', 'crm', 'account'],
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_frontend': [
            'smileliving/static/src/interactions/area_range.js',
            
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
        'views/product_item_inherit.xml',
        'views/wishlist_minimal_tile_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

