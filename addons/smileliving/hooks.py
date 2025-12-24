from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Migrate legacy SmileLiving fields stored on product.template into smileliving.property.

    This module used to _inherit product.template and add real-estate fields.
    We now store them in a vertical model (smileliving.property). The legacy
    DB columns may still exist; we copy data once so nothing is lost.
    """

    env = api.Environment(cr, SUPERUSER_ID, {})

    # If legacy columns do not exist, skip migration.
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'product_template'
           AND column_name = 'is_house'
         LIMIT 1
        """
    )
    if not cr.fetchone():
        return

    # Create property rows for old is_house products (only if not already created).
    cr.execute(
        """
        SELECT pt.id,
               pt.type_id,
               pt.type_sale,
               pt.area,
               pt.house_status,
               pt.description_detail,
               pt.address,
               pt.tinhthanh_id,
               pt.quanhuyen_id,
               pt.phuongxa_id,
               pt.latitude,
               pt.longitude
          FROM product_template pt
         WHERE COALESCE(pt.is_house, FALSE) = TRUE
        """
    )

    Property = env['smileliving.property'].sudo()

    for (
        product_tmpl_id,
        type_id,
        type_sale,
        area,
        house_status,
        description_detail,
        address,
        tinhthanh_id,
        quanhuyen_id,
        phuongxa_id,
        latitude,
        longitude,
    ) in cr.fetchall():
        existing = Property.search([('product_tmpl_id', '=', product_tmpl_id)], limit=1)
        if existing:
            continue

        vals = {
            'product_tmpl_id': product_tmpl_id,
            'type_id': type_id or False,
            'type_sale': type_sale or 'sale',
            'area': float(area or 0.0),
            'house_status': house_status or 'available',
            'description_detail': description_detail or False,
            'address': address or False,
            'tinhthanh_id': tinhthanh_id or False,
            'quanhuyen_id': quanhuyen_id or False,
            'phuongxa_id': phuongxa_id or False,
            'latitude': latitude or 0.0,
            'longitude': longitude or 0.0,
        }
        Property.create(vals)

    # Migrate amenities M2M (product.template -> property)
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'smileliving_product_template_amenity_rel'
         LIMIT 1
        """
    )
    if cr.fetchone():
        cr.execute(
            """
            INSERT INTO smileliving_property_amenity_rel (property_id, amenity_id)
            SELECT p.id, rel.amenity_id
              FROM smileliving_product_template_amenity_rel rel
              JOIN smileliving_property p
                ON p.product_tmpl_id = rel.product_tmpl_id
             WHERE NOT EXISTS (
                   SELECT 1
                     FROM smileliving_property_amenity_rel x
                    WHERE x.property_id = p.id
                      AND x.amenity_id = rel.amenity_id
             )
            """
        )
