# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import re


class SmileLivingController(http.Controller):

    def _website_company(self):
        return request.website.company_id if getattr(request, 'website', None) else request.env.company

    def _map_template_to_company(self, template, company):
        """Map a product.template to the equivalent record in the given company.

        Used to avoid multi-company record rule errors when legacy links point to a
        template owned by another company.
        """
        if not template or not template.exists():
            return template

        if template.company_id and template.company_id.id == company.id:
            return template

        PT = request.env['product.template'].sudo()

        # Prefer mapping via internal reference (default_code)
        code = template.product_variant_id.default_code
        if code:
            target_code = code
            if company.currency_id and company.currency_id.name == 'VND' and not code.endswith('-VN'):
                target_code = f"{code}-VN"
            mapped = PT.search([
                ('company_id', '=', company.id),
                ('product_variant_ids.default_code', '=', target_code),
            ], limit=1)
            if mapped:
                return mapped

        # Fallback mapping by base name (strip trailing '(...)' copy suffix)
        base_name = re.sub(r'\s*\([^)]*\)\s*$', '', (template.name or '')).strip()
        if base_name:
            candidates = PT.search([
                ('company_id', '=', company.id),
                ('name', 'ilike', base_name),
            ], limit=20)
            for candidate in candidates:
                candidate_base = re.sub(r'\s*\([^)]*\)\s*$', '', (candidate.name or '')).strip()
                if candidate_base == base_name:
                    return candidate

        return False
    
    @http.route('/test', type='http', auth='public')
    def test(self):
        return "<h1>Test route works!</h1>"

    @http.route('/smileliving-1', type='http', auth='public', website=True)
    def homepage(self, **kwargs):
        website_company = self._website_company()
        prop_recs = request.env['smileliving.property'].sudo().search([
            ('company_id', 'in', [website_company.id, False]),
        ], order='create_date desc, id desc', limit=4)

        return request.render('smileliving.smileliving_homepage', {
            'properties': prop_recs,
        })
    
    
    @http.route('/smileliving/properties', type='http', auth='public', website=True)
    def property_listing(self, **kwargs):
        return request.not_found()

    @http.route('/smileliving/type/<int:type_id>', type='http', auth='public', website=True, sitemap=False)
    def go_shop_by_type(self, type_id, **kwargs):
        """Redirect helper for Website Builder catalog tiles.

        Example: link a catalog item to /smileliving/type/3
        and it will open /shop filtered to that real-estate type.
        """
        return request.redirect(f"/shop?filter_type_id={type_id}", code=302)
    
    # @http.route('/smileliving/property/<int:property_id>', type='http', auth='public', website=True)
    # def property_detail(self, property_id, **kwargs):
    #     """Chi tiết property"""
    #     website_company = self._website_company()
    #     property = request.env['product.template'].sudo().browse(property_id)
    #     if not property.exists():
    #         return request.not_found()

    #     property = self._map_template_to_company(property, website_company)
    #     if not property:
    #         return request.not_found()
             
    #     return request.render('smileliving.property_detail', {
    #         'property': property,
    #         'google_maps_embed_url': property.google_maps_embed_url,
    #     })
    
    @http.route('/smileliving/interest/<int:property_id>', type='http', auth='public', website=True)
    def show_interest_form(self, property_id, **kwargs):
        """Hiển thị form quan tâm bất động sản"""
        website_company = self._website_company()
        product_tmpl = request.env['product.template'].sudo().browse(property_id)
        if not product_tmpl.exists():
            return request.not_found()

        product_tmpl = self._map_template_to_company(product_tmpl, website_company)
        if not product_tmpl:
            return request.not_found()

        prop = request.env['smileliving.property'].sudo().search([
            ('product_tmpl_id', '=', product_tmpl.id),
        ], limit=1)
        if not prop:
            return request.not_found()
             
        return request.render('smileliving.interest_form', {
            'property': prop,
        })
    
    @http.route('/smileliving/login', type='http', auth='public', website=True)
    def shop_login(self, **kwargs):
        """Trang login riêng cho khách hàng shop muốn hỏi tư vấn"""
        return request.render('smileliving.smileliving_shop_login', {
            'redirect': kwargs.get('redirect') or '/shop',
            'login_error': bool(request.params.get('login_error')),
        })

    @http.route('/smileliving/submit_interest/<int:property_id>', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def submit_interest(self, property_id, **kwargs):
        """Xử lý submit form quan tâm và tạo CRM Lead"""
        try:
            website_company = self._website_company()
            lead_model = request.env['crm.lead'].sudo().with_company(website_company)
            product_tmpl = request.env['product.template'].sudo().browse(property_id)
            if not product_tmpl.exists():
                return request.redirect('/smileliving?error=property_not_found')

            product_tmpl = self._map_template_to_company(product_tmpl, website_company)
            if not product_tmpl:
                return request.redirect('/smileliving?error=property_not_found')

            prop = request.env['smileliving.property'].sudo().search([
                ('product_tmpl_id', '=', product_tmpl.id),
            ], limit=1)
            if not prop:
                return request.redirect('/smileliving?error=property_not_found')
            
            # Lấy thông tin từ form
            name = kwargs.get('name', '').strip()
            email = kwargs.get('email', '').strip()
            phone = kwargs.get('phone', '').strip()
            message = kwargs.get('message', '').strip()
            
            # Validate
            if not name or not email or not phone:
                return request.render('smileliving.interest_form', {
                    'property': prop,
                    'error': 'Vui lòng điền đầy đủ thông tin bắt buộc',
                    'values': kwargs
                })
            
            # Tạo hoặc tìm partner
            partner = False
            if email:
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
                if not partner:
                    partner = request.env['res.partner'].sudo().create({
                        'name': name,
                        'email': email,
                        'phone': phone,
                    })
            
            # Tạo CRM Lead
            lead_name = f"Quan tâm: {product_tmpl.name} - {name}"
            description = f"""
            Khách hàng quan tâm bất động sản:
            - Tên bất động sản: {product_tmpl.name}
            - Địa chỉ: {prop.address}
            - Giá: {product_tmpl.list_price:,.0f} VNĐ
            - Diện tích: {prop.area} m²
            - Loại hình: {prop.type_id.name if prop.type_id else 'Chưa xác định'}
            - Trạng thái: {dict(prop._fields['house_status'].selection).get(prop.house_status) if 'house_status' in prop._fields else (prop.house_status or '')}
            
            Thông tin khách hàng:
            - Họ tên: {name}
            - Email: {email}
            - Số điện thoại: {phone}
            - Tin nhắn: {message or 'Không có'}
            """
            
            # Lấy UTM và team với sudo để tránh lỗi permissions
            medium_id = False
            source_id = False
            team_id = False
            
            try:
                medium_id = request.env.ref('utm.utm_medium_website').sudo().id
            except:
                pass
                
            try:
                source_id = request.env.ref('utm.utm_source_website').sudo().id
            except:
                pass
                
            try:
                team_id = request.env['crm.team'].sudo().with_company(website_company).search([
                    '|', ('company_id', '=', False), ('company_id', '=', website_company.id)
                ], limit=1).id
            except:
                pass
            
            # Thử tạo lead với priority
            lead_vals = {
                'name': lead_name,
                'description': description,
                'type': 'lead',
                'partner_id': partner.id if partner else False,
                'email_from': email,
                'phone': phone,
                'medium_id': medium_id,
                'source_id': source_id,
                'team_id': team_id,
                'company_id': website_company.id,
                'expected_revenue': product_tmpl.list_price,
                'smile_product_tmpl_id': product_tmpl.id,
                'smile_property_id': prop.id,
            }
            
            # Thêm priority với fallback
            try:
                lead_vals['priority'] = 'high'  # Thử string trước
                lead = lead_model.create(lead_vals)
            except:
                try:
                    lead_vals['priority'] = '2'  # Thử numeric
                    lead = lead_model.create(lead_vals)
                except:
                    # Bỏ priority nếu không hợp lệ
                    lead = lead_model.create(lead_vals)
            
            # Ghi log vào property
            product_tmpl.sudo().message_post(body=f"Đã tạo CRM Lead <a href='#' data-oe-model='crm.lead' data-oe-id='{lead.id}'>{lead.name}</a> từ quan tâm của khách hàng {name}")
            
            # Redirect đến trang cảm ơn
            return request.render('smileliving.interest_success', {
                'property': prop,
                'customer_name': name,
                'lead_id': lead.id
            })
                
        except Exception as e:
            # Log lỗi để debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in submit_interest: {str(e)}")
            
            # Trả về form với lỗi
            try:
                product_tmpl = request.env['product.template'].sudo().browse(property_id)
                prop = request.env['smileliving.property'].sudo().search([
                    ('product_tmpl_id', '=', product_tmpl.id),
                ], limit=1)
                return request.render('smileliving.interest_form', {
                    'property': prop,
                    'error': f'Có lỗi xảy ra: {str(e)}',
                    'values': kwargs
                })
            except:
                return request.redirect('/smileliving?error=general_error')

    @http.route('/smileliving/wishlist/interest', type='json', auth='public', website=True)
    def wishlist_interest(self, product_id, **kw):
        """Create a crm.lead when a visitor clicks 'Quan tâm' on a wishlist product (JSON route)."""
        try:
            website_company = request.website.company_id if getattr(request, 'website', None) else request.env.company
            lead_model = request.env['crm.lead'].sudo().with_company(website_company)
            product = request.env['product.product'].sudo().browse(int(product_id))
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}

            product_tmpl = product.product_tmpl_id
            prop = request.env['smileliving.property'].sudo().search([
                ('product_tmpl_id', '=', product_tmpl.id),
            ], limit=1)
            team_id = False
            try:
                team_id = request.env['crm.team'].sudo().with_company(website_company).search([
                    '|', ('company_id', '=', False), ('company_id', '=', website_company.id)
                ], limit=1).id
            except:
                pass
            lead = lead_model.create({
                'name': f"Quan tâm {product.display_name}",
                'type': 'opportunity',
                'description': f"Sản phẩm wishlist: {product.display_name} (id: {product.id})",
                'team_id': team_id,
                'company_id': website_company.id,
                'expected_revenue': product_tmpl.list_price,
                'smile_product_tmpl_id': product_tmpl.id,
                'smile_property_id': prop.id if prop else False,
            })
            return {'success': True, 'lead_id': lead.id}
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception('Error creating wishlist interest lead: %s', e)
            return {'success': False, 'error': 'server error'}

    # Same behavior as above, but exposed under the Website Sale wishlist URL namespace.
    # This keeps the frontend route consistent with `/shop/wishlist` (no `/smileliving` prefix).
    @http.route('/shop/wishlist/interest', type='json', auth='public', website=True)
    def shop_wishlist_interest(self, product_id, **kw):
        return self.wishlist_interest(product_id, **kw)

    # ------------------------------------------------------------------
    # Project listing & detail (website)
    # ------------------------------------------------------------------

    @http.route(['/projects', '/du-an'], type='http', auth='public', website=True)
    def project_list(self, **kwargs):
        website_company = self._website_company()
        Project = request.env['smileliving.project'].sudo().with_context(active_test=True)
        projects = Project.search([
            ('company_id', 'in', [website_company.id, False]),
            ('active', '=', True),
        ], order='start_date desc, id desc')

        return request.render('smileliving.project_list', {
            'projects': projects,
        })

    @http.route('/projects/<model("smileliving.project"):project>', type='http', auth='public', website=True)
    def project_detail(self, project, **kwargs):
        website_company = self._website_company()

        if project.company_id and project.company_id.id not in (website_company.id,):
            return request.not_found()

        props = request.env['smileliving.property'].sudo().search([
            ('project_id', '=', project.id),
        ], limit=4, order='create_date desc, id desc')

        return request.render('smileliving.project_detail', {
            'project': project.sudo(),
            'sample_properties': props,
        })
