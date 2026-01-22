from odoo import api, fields, models, _


class SmileLivingPropertySubmission(models.Model):
    _name = 'smileliving.property.submission'
    _description = 'Property Submission (user uploaded)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tiêu đề', required=True)
    related_property_id = fields.Many2one('smileliving.property', string='Property (if any)', index=True)
    uploader_id = fields.Many2one('res.users', string='Người gửi', default=lambda self: self.env.uid)
    contact_info = fields.Char(string='Thông tin liên hệ')
    price = fields.Float(string='Giá')
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id.id)
    type_id = fields.Many2one('smileliving.type', string='Loại bất động sản')
    type_sale = fields.Selection([('sale','Mua bán'), ('rent','Cho thuê')], string='Hình thức', default='sale')
    area = fields.Float(string='Diện tích')
    bedroom_count = fields.Integer(string='Phòng ngủ', default=0)
    bathroom_count = fields.Integer(string='WC', default=0)
    description = fields.Text(string='Mô tả')
    state = fields.Selection([
        ('draft','Nháp'),
        ('pending','Đang chờ'),
        ('reviewed','Đã xem'),
        ('rejected','Bị từ chối'),
        ('approved','Đã duyệt'),
    ], string='Trạng thái', default='draft', index=True, tracking=True)
    submitted_at = fields.Datetime(string='Ngày gửi')
    reviewed_by = fields.Many2one('res.users', string='Người duyệt')
    reviewed_at = fields.Datetime(string='Ngày duyệt')
    rejection_reason = fields.Text(string='Lý do từ chối')

    # Attachments: images/documents uploaded by user are stored in ir.attachment
    # linked via (res_model, res_id). Expose them as a m2m so we can use
    # standard widgets like many2many_binary in backend views.
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tệp đính kèm',
        compute='_compute_attachment_ids',
        inverse='_inverse_attachment_ids',
    )

    def _compute_attachment_ids(self):
        Attachment = self.env['ir.attachment'].sudo()
        for rec in self:
            if not rec.id:
                rec.attachment_ids = False
                continue
            rec.attachment_ids = Attachment.search([
                ('res_model', '=', 'smileliving.property.submission'),
                ('res_id', '=', rec.id),
            ])

    def _inverse_attachment_ids(self):
        Attachment = self.env['ir.attachment'].sudo()
        for rec in self:
            if not rec.id:
                continue
            current = Attachment.search([
                ('res_model', '=', 'smileliving.property.submission'),
                ('res_id', '=', rec.id),
            ])
            desired = rec.attachment_ids
            (desired - current).write({'res_model': 'smileliving.property.submission', 'res_id': rec.id})
            (current - desired).write({'res_model': False, 'res_id': 0})

    @api.model
    def _generate_product_code(self):
        seq = self.env['ir.sequence'].sudo()
        seq_code = 'VNRE'
        try:
            s = seq.next_by_code('smileliving.product.code')
        except Exception:
            # fallback: use id-based code
            s = False
        if not s:
            # use timestamp fallback
            import time
            s = f"{seq_code}-{int(time.time())}"
        return s

    def action_submit(self):
        for rec in self:
            rec.state = 'pending'
            rec.submitted_at = fields.Datetime.now()
            rec.message_post(body=_('Submission submitted for review'))
        return True

    def action_reject(self, reason=None):
        for rec in self:
            rec.state = 'rejected'
            rec.reviewed_by = self.env.uid
            rec.reviewed_at = fields.Datetime.now()
            if reason:
                rec.rejection_reason = reason
            rec.message_post(body=_('Submission rejected: %s' % (rec.rejection_reason or _('No reason'))))
        return True

    def action_approve_and_convert(self, publish=False):
        ProductTmpl = self.env['product.template'].sudo()
        Property = self.env['smileliving.property'].sudo()
        for rec in self:
            # If already linked to a property/product, just mark approved
            if rec.related_property_id and rec.related_property_id.product_tmpl_id:
                rec.state = 'approved'
                rec.reviewed_by = self.env.uid
                rec.reviewed_at = fields.Datetime.now()
                rec.message_post(body=_('Submission approved and linked to existing property.'))
                continue

            # Create product.template
            company = Property._get_vn_company()
            tmpl_vals = {
                'name': rec.name,
                'sale_ok': True,
                'purchase_ok': False,
                'company_id': company.id,
                'list_price': float(rec.price or 0.0),
            }
            if 'is_published' in ProductTmpl._fields:
                tmpl_vals['is_published'] = bool(publish)
            elif 'website_published' in ProductTmpl._fields:
                tmpl_vals['website_published'] = bool(publish)
            if 'detailed_type' in ProductTmpl._fields:
                tmpl_vals['detailed_type'] = 'service'
            elif 'type' in ProductTmpl._fields:
                tmpl_vals['type'] = 'service'

            tmpl = ProductTmpl.create(tmpl_vals)
            # set variant default_code
            try:
                if tmpl.product_variant_id:
                    code = self._generate_product_code()
                    tmpl.product_variant_id.default_code = code
            except Exception:
                pass

            # Move attachments: re-assign attachments to product.template
            for att in rec.attachment_ids:
                try:
                    att.write({'res_model': 'product.template', 'res_id': tmpl.id})
                except Exception:
                    pass

            # Create property record
            prop_vals = {
                'product_tmpl_id': tmpl.id,
                'type_id': rec.type_id.id if rec.type_id else False,
                'type_sale': rec.type_sale or 'sale',
                'area': float(rec.area or 0.0),
                'bedroom_count': int(rec.bedroom_count or 0),
                'bathroom_count': int(rec.bathroom_count or 0),
                'house_status': 'available',
                'address': rec.name,
                'description_detail': rec.description,
            }
            new_prop = Property.create(prop_vals)

            rec.related_property_id = new_prop.id
            rec.state = 'approved'
            rec.reviewed_by = self.env.uid
            rec.reviewed_at = fields.Datetime.now()
            rec.message_post(body=_('Submission approved and converted to product/property.'))
        return True
