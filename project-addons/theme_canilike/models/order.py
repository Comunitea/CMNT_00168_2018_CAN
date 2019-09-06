# -*- coding: utf-8 -*-
#
##############################################################################
#
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    © 2019 Comunitea - Ruben Seijas <ruben@comunitea.com>
#    © 2019 Comunitea - Pavel Smirnov <pavel@comunitea.com>
#    © 2019 Comunitea - Vicente Gutiérrez <vicente@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_shipping_location(self, current_country, partner_shipping_id=False):

        shipping_country_id = self.partner_shipping_id.country_id
        if partner_shipping_id:
            shipping_country_id = partner_shipping_id.country_id
        
        country_ids = current_country.country_ids
        result = shipping_country_id in country_ids
        return result