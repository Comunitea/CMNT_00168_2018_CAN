# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def get_website_available(self, not_current=False):
        domain = [('website_available', '=', True)]
        if not_current:
            domain.append(('id', '!=', self.get_current_country().id))
        return self.env['res.country.group'].search(domain)

    def get_current_country(self):
        country_code = request.session['geoip'].get('country_code')
        if not country_code:
            request.session['geoip']['country_code'] = \
                self.company_id.country_id.code
            return self.get_current_country()
        return self.env['res.country.group'].search(
            [('country_code', '=', country_code)])

    def _prepare_sale_order_values(self, partner, pricelist):
        res = super()._prepare_sale_order_values(partner, pricelist)
        country = self.get_current_country()
        res['warehouse_id'] = self.env['stock.warehouse'].sudo(
            ).get_warehouse_id(country.country_code).id
        res['fiscal_position_id'] = country.fiscal_position_id.id
        return res
