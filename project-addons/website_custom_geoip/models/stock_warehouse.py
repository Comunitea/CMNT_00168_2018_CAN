# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, fields


class StockWarehouse(models.Model):

    _inherit = 'stock.warehouse'

    country_group_id = fields.Many2many(
        'res.country.group', string='Country Groups')

    @api.model
    def get_warehouse_id(self, country_code):
        warehouse = self.env['stock.warehouse'].search(
            [('country_group_id.country_ids.code', '=', country_code)],
            limit=1
        )
        return warehouse
