# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields

class StockWarehouse(models.Model):

    _inherit = 'stock.warehouse'

    @api.model
    def get_warehouse_id(self, country_code):
        res = super(StockWarehouse, self).get_warehouse_id(country_code)
        if not res:
            res = self.env['stock.warehouse'].search(
                [('code', '=', country_code)],
                limit=1
            )
        return res