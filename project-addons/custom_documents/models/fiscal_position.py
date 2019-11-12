# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    custom_vat = fields.Char()
    custom_text = fields.Char()
