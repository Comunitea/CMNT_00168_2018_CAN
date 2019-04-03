# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.website_sale_stock.controllers.main import WebsiteSale
from odoo.http import route, request


class WebsiteSaleGeoIp(WebsiteSale):

    def get_attribute_value_ids(self, product):
        country_code = request.session['geoip'].get('country_code')
        if country_code:
            warehouse = request.env['stock.warehouse'].sudo().get_warehouse_id(
                country_code)
            if warehouse:
                context = request.env.context.copy()
                context.update({'warehouse': warehouse.id})
                request.env.context = context
        return super(WebsiteSaleGeoIp, self).get_attribute_value_ids(product)

    @route(['/change_country/<string:country_code>'], type='http',
           auth="public",  website=True)
    def change_country(self, country_code, **post):
        request.website.sale_reset()
        request.session['geoip']['country_code'] = country_code
        return request.redirect("/")
