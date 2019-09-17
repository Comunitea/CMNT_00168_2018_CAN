# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    country_code = fields.Char()
    website_available = fields.Boolean()
    warehouse_ids = fields.Many2many('stock.warehouse', 'country_group_id')
    fiscal_position_id = fields.Many2one('account.fiscal.position')

    def get_flag(self):
        return self.country_ids[0].image


class ResCountry(models.Model):

    _inherit = 'res.country'

    def create_country_group(self):
        for country in self:
            self.env['res.country.group'].create({
                'name': country.name,
                'country_code': country.code,
                'country_ids': [(4, country.id)]
            })
