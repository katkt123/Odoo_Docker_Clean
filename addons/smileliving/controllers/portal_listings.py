# -*- coding: utf-8 -*-

import base64

from odoo import http
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
            'submitted_at': request.env['ir.fields.converter'].to_datetime(post.get('submitted_at')) if post.get('submitted_at') else None,
        }
        if not vals['submitted_at']:
            vals['submitted_at'] = request.env['ir.fields'].Datetime.now()

        submission = Submission.create(vals)

        # Attach uploaded files
        files = request.httprequest.files.getlist('attachments')
        if files:
            Attachment = request.env['ir.attachment'].sudo()
            for f in files:
                if not f or not getattr(f, 'filename', None):
                    continue
                content = f.read()
                if not content:
                    continue
                Attachment.create({
                    'name': f.filename,
                    'datas': base64.b64encode(content),
                    'res_model': 'smileliving.property.submission',
                    'res_id': submission.id,
                    'mimetype': getattr(f, 'mimetype', None),
                })

        try:
            submission.message_post(body='User submitted from website.')
        except Exception:
            pass

        return request.redirect('/smileliving/manage?status=pending')
