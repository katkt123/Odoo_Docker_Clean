# estate_property_offer.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Đề nghị giá (Bidding)"
    _order = "price desc"

    price = fields.Float("Giá đề nghị", required=True)
    partner_id = fields.Many2one("res.partner", string="Khách hàng", required=True)
    property_id = fields.Many2one("estate.property", string="Bất động sản", required=True)
    
    status = fields.Selection([
        ('pending', 'Đang chờ'),
        ('accepted', 'Chấp nhận'),
        ('refused', 'Từ chối')
    ], string="Trạng thái", copy=False, default='pending')

    # Khi chấp nhận Offer -> Tự động tạo Phiếu Đặt Cọc (Deposit)
    def action_accept(self):
        for record in self:
            _logger.info(f"Starting action_accept for offer {record.id}")
            
            # Chấp nhận đề nghị hiện tại
            record.status = 'accepted'
            _logger.info(f"Set offer status to accepted")
            
            # Cập nhật thông tin BĐS
            record.property_id.state = 'sold'
            record.property_id.buyer_id = record.partner_id
            record.property_id.selling_price = record.price
            _logger.info(f"Updated property {record.property_id.id} state to sold")
            
            # Từ chối tất cả các đề nghị khác
            other_offers = record.property_id.offer_ids.filtered(lambda offer: offer.id != record.id)
            if other_offers:
                other_offers.write({'status': 'refused'})
                _logger.info(f"Refused {len(other_offers)} other offers")
            
            # Tạo deposit
            try:
                deposit = self.env['estate.property.deposit'].create({
                    'property_id': record.property_id.id,
                    'partner_id': record.partner_id.id,
                    'amount': record.price * 0.1,
                    'note': f"Đặt cọc theo offer giá {record.price}"
                })
                _logger.info(f"Created deposit {deposit.name} for offer {record.id}")
                
                # Hiển thị thông báo thành công
                message = f"Đã chấp nhận đề nghị {record.price:,.0f}. Tạo deposit {deposit.name} thành công!"
                
            except Exception as e:
                _logger.error(f"Failed to create deposit: {str(e)}")
                raise UserError(f"Không thể tạo deposit: {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công!',
                'message': message.strip(),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_refuse(self):
        """Từ chối đề nghị"""
        for record in self:
            record.status = 'refused'
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đã từ chối',
                'message': f'Đề nghị {self.price:,.0f} đã bị từ chối',
                'type': 'warning',
                'sticky': False,
            }
        }