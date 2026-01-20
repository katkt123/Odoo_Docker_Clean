# -*- coding: utf-8 -*-

import base64

from odoo import http, fields
from odoo.http import request


class SmileLivingPortalListings(http.Controller):
    def _user_submission_domain(self):
        return [('uploader_id', '=', request.env.user.id)]

    def _get_submission_counts(self, submissions):
        counts = {
            'all': len(submissions),
            'published': 0,
            'approved_hidden': 0,
            'pending': 0,
            'rejected': 0,
            'draft': 0,
        }
        for rec in submissions:
            if rec.state == 'draft':
                counts['draft'] += 1
                continue
            if rec.state in ('pending', 'reviewed'):
                counts['pending'] += 1
                continue
            if rec.state == 'rejected':
                counts['rejected'] += 1
                continue
            if rec.state == 'approved':
                prop = rec.related_property_id
                if prop and prop.is_publish:
                    counts['published'] += 1
                else:
                    counts['approved_hidden'] += 1
        return counts

    def _filter_submissions(self, submissions, status):
        status = (status or 'all').strip()
        if status == 'all':
            return submissions
        if status == 'draft':
            return submissions.filtered(lambda r: r.state == 'draft')
        if status == 'pending':
            return submissions.filtered(lambda r: r.state in ('pending', 'reviewed'))
        if status == 'rejected':
            return submissions.filtered(lambda r: r.state == 'rejected')
        if status == 'published':
            return submissions.filtered(lambda r: r.state == 'approved' and r.related_property_id and r.related_property_id.is_publish)
        if status == 'approved_hidden':
            return submissions.filtered(lambda r: r.state == 'approved' and (not r.related_property_id or not r.related_property_id.is_publish))
        return submissions

    @http.route(['/smileliving/manage'], type='http', auth='user', website=True, sitemap=False)
    def manage_listings(self, status='published', q=None, **kwargs):
        Submission = request.env['smileliving.property.submission']

        submissions = Submission.search(self._user_submission_domain(), order='create_date desc, id desc')
        counts = self._get_submission_counts(submissions)

        filtered = self._filter_submissions(submissions, status)
        if q:
            q_norm = q.strip().lower()
            if q_norm:
                filtered = filtered.filtered(lambda r: (r.name or '').lower().find(q_norm) >= 0)

        return request.render('smileliving.portal_manage_listings', {
            'status': status or 'published',
            'q': q or '',
            'counts': counts,
            'submissions': filtered,
        })

    @http.route(['/smileliving/submit'], type='http', auth='user', website=True, sitemap=False)
    def submit_listing_form(self, **kwargs):
        # 'smileliving.type' has no 'sequence' field in this DB; order by name instead
        types = request.env['smileliving.type'].sudo().search([], order='name, id')
        user = request.env.user
        contact_info = ''
        if user.partner_id:
            parts = []
            if user.partner_id.phone:
                parts.append(user.partner_id.phone)
            if user.partner_id.email:
                parts.append(user.partner_id.email)
            contact_info = ' | '.join(parts)
        return request.render('smileliving.portal_submit_listing', {
            'types': types,
            'contact_info': contact_info,
            'error': kwargs.get('error'),
            'values': kwargs,
        })

    @http.route(['/smileliving/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit_listing_post(self, **post):
        Submission = request.env['smileliving.property.submission']

        name = (post.get('name') or '').strip()
        if not name:
            return self.submit_listing_form(error='Vui lòng nhập tiêu đề.', **post)

        vals = {
            'name': name,
            'contact_info': (post.get('contact_info') or '').strip(),
            'type_sale': post.get('type_sale') or 'sale',
            'type_id': int(post['type_id']) if post.get('type_id') else False,
            'area': float(post.get('area') or 0.0),
            'price': float(post.get('price') or 0.0),
            'description': (post.get('description') or '').strip(),
            'uploader_id': request.env.user.id,
            'state': 'pending',
            'submitted_at': post.get('submitted_at') or fields.Datetime.now(),
        }

        try:
            # Create submission as sudo to avoid portal permission issues,
            # but keep uploader_id as the real user.
            submission = Submission.sudo().create(vals)
            # Log success so we can trace submissions from website in logs
            try:
                request.env['ir.logging'].sudo().create({
                    'name': 'smileliving.submit_success',
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': request.cr.dbname,
                    'message': 'Created submission id=%s uploader=%s' % (submission.id, vals.get('uploader_id')),
                    'path': 'smileliving.controllers.portal_listings',
                })
            except Exception:
                pass
        except Exception as e:
            _logger = request.env['ir.logging']
            try:
                _logger.sudo().create({
                    'name': 'smileliving.submit_error',
                    'type': 'server',
                    'level': 'ERROR',
                    'dbname': request.cr.dbname,
                    'message': 'Failed creating submission: %s' % (str(e),),
                    'path': 'smileliving.controllers.portal_listings',
                })
            except Exception:
                pass
            return self.submit_listing_form(error='Lỗi nội bộ, không thể tạo đơn. Vui lòng thử lại.', **post)

        # Attach uploaded files (create as sudo and ensure base64 string)
        files = request.httprequest.files.getlist('attachments')
        if files:
            Attachment = request.env['ir.attachment'].sudo()
            for f in files:
                if not f or not getattr(f, 'filename', None):
                    continue
                try:
                    content = f.read()
                    if not content:
                        continue
                    Attachment.create({
                        'name': f.filename,
                        'datas': base64.b64encode(content).decode('utf-8') if isinstance(base64.b64encode(content), bytes) else base64.b64encode(content),
                        'res_model': 'smileliving.property.submission',
                        'res_id': submission.id,
                        'mimetype': getattr(f, 'mimetype', None),
                    })
                except Exception as e:
                    # log attachment errors but continue
                    try:
                        request.env['ir.logging'].sudo().create({
                            'name': 'smileliving.attachment_error',
                            'type': 'server',
                            'level': 'WARNING',
                            'dbname': request.cr.dbname,
                            'message': 'Attachment save failed: %s' % (str(e),),
                            'path': 'smileliving.controllers.portal_listings',
                        })
                    except Exception:
                        pass

        try:
            submission.message_post(body='User submitted from website.')
        except Exception:
            pass

        return request.redirect('/smileliving/manage?status=pending')

    @http.route(['/smileliving/map'], type='http', auth='public', website=True, sitemap=False)
    def map_view(self, **kw):
        return request.render('smileliving.portal_map', {})

    @http.route(['/smileliving/map_data'], type='http', auth='public', website=True, csrf=False)
    def map_data(self, **kw):
        Property = request.env['smileliving.property'].sudo()
        ProductTmpl = request.env['product.template'].sudo()
        # Determine which publish flag exists on product.template (is_published or website_published)
        publish_field = None
        if 'is_published' in ProductTmpl._fields:
            publish_field = 'is_published'
        elif 'website_published' in ProductTmpl._fields:
            publish_field = 'website_published'

        # If product.template exposes a publish field, filter properties by that field
        if publish_field:
            domain = [('product_tmpl_id', '!=', False), (f'product_tmpl_id.{publish_field}', '=', True)]
        else:
            # Fallback: include all properties linked to a product template
            domain = [('product_tmpl_id', '!=', False)]

        props = Property.search(domain)
        features = []
        for p in props:
            try:
                lat = float(p.latitude or 0.0)
                lon = float(p.longitude or 0.0)
            except Exception:
                continue
            if not lat or not lon:
                continue
            thumb = ''
            try:
                thumb = request.env['ir.http'].sudo().image_url(p, 'product_image_1920') or ''
            except Exception:
                thumb = ''
            price = 0.0
            try:
                price = float(getattr(p, 'price_vnd', 0.0) or (p.product_tmpl_id and p.product_tmpl_id.list_price) or 0.0)
            except Exception:
                price = 0.0
            url = '/smileliving/manage'
            try:
                if p.product_tmpl_id and getattr(p.product_tmpl_id, 'website_url', False):
                    url = p.product_tmpl_id.website_url
            except Exception:
                pass
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
                'properties': {
                    'id': p.id,
                    'title': p.name,
                    'price': price,
                    'thumb': thumb,
                    'url': url,
                }
            })
        return request.make_json_response({'type': 'FeatureCollection', 'features': features})
