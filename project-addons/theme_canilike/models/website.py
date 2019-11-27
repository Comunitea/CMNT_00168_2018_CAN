# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.http import request

class Website(models.Model):
    _inherit = 'website'

    def get_available_countries(self):
        country_code = request.session['geoip'].get('country_code')
        
        warehouse_countries = self.env['stock.warehouse'].sudo().get_warehouse_id(country_code)\
            .country_group_id.mapped('country_ids')
        return warehouse_countries