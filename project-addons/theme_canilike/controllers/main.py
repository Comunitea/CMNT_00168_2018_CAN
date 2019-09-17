# -*- coding: utf-8 -*-
import json
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, tools, _
from odoo.http import request

class WebsiteSale(http.Controller):

    @http.route(['/shop/check_if_allowed_addres'], type='json', auth="public", methods=['POST'], website=True)
    def check_if_allowed_addres(self, partner_id, **kw):
        
        country_code = request.session['geoip'].get('country_code')
        warehouse_countries = request.env['stock.warehouse'].get_warehouse_id(country_code)\
            .country_group_id.mapped('country_ids').mapped('code')
        shipping_country = request.env['res.partner'].browse(partner_id).country_id.code
        result = shipping_country in warehouse_countries

        return result