# -*- coding: utf-8 -*-

import base64

from odoo import http, fields
from odoo.http import request


class SmileLivingPortalListings(http.Controller):
    def _to_float(self, value):
        """Best-effort float parser that tolerates commas/spaces."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except Exception:
            try:
                normalized = str(value).replace(',', '').replace(' ', '')
                return float(normalized)
            except Exception:
                return 0.0

    def _to_int(self, value):
        if value is None:
            return 0
        s = str(value).strip()
        if not s:
            return 0
        try:
            return int(s)
        except Exception:
            try:
                normalized = s.replace(',', '').replace(' ', '')
                return int(float(normalized))
            except Exception:
                return 0

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
            if rec.state == 'pending':
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
            return submissions.filtered(lambda r: r.state == 'pending')
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
        # Breadcrumb log to confirm GET form hits this controller
        try:
            from odoo import registry
            with registry(request.cr.dbname).cursor() as cr:
                cr.autocommit = True
                cr.execute(
                    """
                    INSERT INTO ir_logging (create_date, name, type, level, dbname, message, path, func, line)
                    VALUES (NOW(), %s, 'server', 'INFO', %s, %s, 'smileliving.controllers.portal_listings', 'submit_listing_form', 0)
                    """,
                    ['smileliving.submit_get', request.cr.dbname, f"uid={user.id} editable={bool(request.params.get('editable'))}"]
                )
        except Exception:
            pass
        if user.partner_id:
            parts = []
            if user.partner_id.phone:
                parts.append(user.partner_id.phone)
            if user.partner_id.email:
                parts.append(user.partner_id.email)
            contact_info = ' | '.join(parts)
        raw_feedback = kwargs.get('feedback') or request.params.get('feedback')
        feedback = kwargs.pop('feedback', None)
        error = kwargs.pop('error', None)
        values = dict(kwargs)
        session_feedback = request.session.pop('smile_submit_feedback', None)
        if session_feedback and not feedback:
            feedback = session_feedback
        # Also accept feedback via query param (?feedback=success)
        if raw_feedback == 'success' and not (isinstance(feedback, dict) and feedback.get('type')):
            feedback = {
                'type': 'success',
                'text': 'Thông tin đã được gửi đi. Đội ngũ SmileLiving sẽ kiểm tra và phản hồi sau.',
            }
        # Normalize feedback: only allow dict with expected keys
        if feedback and not isinstance(feedback, dict):
            feedback = None

        return request.render('smileliving.portal_submit_listing', {
            'types': types,
            'contact_info': contact_info,
            'error': error,
            'values': values,
            'feedback': feedback,
        })

    @http.route(['/smileliving/submit/proptech'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit_listing_post(self, **post):
        Submission = request.env['smileliving.property.submission']

        # Debug: append payload to a file inside container so we can confirm controller runs
        try:
            debug_path = '/var/lib/odoo/smile_submit_debug.log'
            with open(debug_path, 'a', encoding='utf-8') as fh:
                fh.write('---- SUBMIT CALL ----\n')
                from datetime import datetime
                fh.write(datetime.utcnow().isoformat() + ' UTC\n')
                fh.write('user_id=%s\n' % (request.env.user.id,))
                for k, v in post.items():
                    # avoid writing binary
                    try:
                        fh.write('%s=%s\n' % (k, str(v)))
                    except Exception:
                        fh.write('%s=<unserializable>\n' % (k,))
                fh.write('\n')
        except Exception:
            pass

        # If debug param provided, immediately return a simple response for fast feedback
        if post.get('debug'):
            return request.make_response('ok')

        def _log_event(name, message):
            try:
                request.env['ir.logging'].sudo().create({
                    'name': name,
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': request.cr.dbname,
                    'message': message,
                    'path': 'smileliving.controllers.portal_listings',
                    'func': 'submit_listing_post',
                    'line': 0,
                })
            except Exception:
                pass

        # Trace incoming payload (without files)
        _log_event(
            'smileliving.submit_received',
            f"uid={request.env.user.id} name={post.get('name','').strip()} type_id={post.get('type_id')} price={post.get('price')} area={post.get('area')} bed={post.get('bedroom_count')} wc={post.get('bathroom_count')}"
        )

        name = (post.get('name') or '').strip()
        if not name:
            return self.submit_listing_form(error='Vui lòng nhập tiêu đề.', **post)

        vals = {
            'name': name,
            'contact_info': (post.get('contact_info') or '').strip(),
            'type_sale': post.get('type_sale') or 'sale',
            'type_id': int(post['type_id']) if post.get('type_id') else False,
            'area': self._to_float(post.get('area')),
            'bedroom_count': self._to_int(post.get('bedroom_count')),
            'bathroom_count': self._to_int(post.get('bathroom_count')),
            'price': self._to_float(post.get('price')),
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
            _log_event('smileliving.submit_success', 'Created submission id=%s uploader=%s' % (submission.id, vals.get('uploader_id')))

            request.session['smile_submit_feedback'] = {
                'type': 'success',
                'text': 'Thông tin đã được gửi đi. Đội ngũ SmileLiving sẽ kiểm tra và phản hồi sau.',
                
            }
            # --- Ensure admins are aware and can approve ---
            try:
                # Collect admin-like users: system administrators and website publishers
                admin_users = set()
                try:
                    grp_sys = request.env.ref('base.group_system')
                    admin_users.update(u.id for u in grp_sys.users)
                except Exception:
                    pass
                try:
                    grp_pub = request.env.ref('website.group_website_publisher')
                    admin_users.update(u.id for u in grp_pub.users)
                except Exception:
                    pass

                admin_users = [u for u in admin_users if u]
                # Subscribe their partners to the submission thread so it appears in chatter
                partner_ids = []
                for uid in admin_users:
                    try:
                        user = request.env['res.users'].sudo().browse(uid)
                        if user and user.partner_id:
                            partner_ids.append(user.partner_id.id)
                    except Exception:
                        continue
                if partner_ids:
                    try:
                        submission.sudo().message_subscribe(partner_ids=partner_ids)
                    except Exception:
                        pass

                # Create a todo activity for each admin user (so it shows in their To-Do inbox)
                Activity = request.env['mail.activity'].sudo()
                for uid in admin_users:
                    try:
                        Activity.create({
                            'res_model_id': request.env['ir.model'].sudo().search([('model', '=', 'smileliving.property.submission')], limit=1).id,
                            'res_id': submission.id,
                            'user_id': uid,
                            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
                            'summary': f"Phê duyệt tin: {submission.name}",
                        })
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            _log_event('smileliving.submit_error', 'Failed creating submission: %s' % (str(e),))
            feedback = {
                'type': 'error',
                'text': 'Lỗi nội bộ, không thể tạo đơn. Vui lòng thử lại.',
                'details': str(e),
            }
            return self.submit_listing_form(error='Lỗi nội bộ, không thể tạo đơn. Vui lòng thử lại.', feedback=feedback, **post)

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

        return request.redirect('/smileliving/submit?feedback=success')

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
