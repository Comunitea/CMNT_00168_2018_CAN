# -*- coding: utf-8 -*-
import json
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, tools, _
from odoo.http import request

class WebsiteSale(http.Controller):

    @http.route(['/shop/check_if_allowed_addres'], type='json', auth="public", methods=['POST'], website=True)
    def check_if_allowed_addres(self, current_country, partner_id, **kw):
        
        country_ids = request.env['res.country.group'].browse(current_country).country_ids
        shipping_country_id = request.env['res.partner'].browse(partner_id).country_id

        result = shipping_country_id in country_ids

        return result