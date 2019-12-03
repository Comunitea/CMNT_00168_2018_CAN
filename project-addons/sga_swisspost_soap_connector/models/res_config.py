# -*- coding: utf-8 -*-
##############################################################################
#    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#    Copyright (C) 2019 Comunitea Servicios Tecnológicos S.L. All Rights Reserved
#    Vicente Ángel Gutiérrez <vicente@comunitea.com>
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
from odoo import fields, models, api, _

SOAP_PARAMS = ['sender_id', 'depositor_no', 'partner_no', 'warehouse_id', 'supplier_no', 'email_alarm', \
    'sprach_code', 'operating_mode', 'soap_url', 'certificate_file', 'certificate_key_file', 'certificate_password']

class ConfigSoapData(models.TransientModel):

    _inherit = 'res.config.settings'

    sender_id = fields.Char('Sender-ID', help="ID given by Swiss Post.", default="Testshop99")
    depositor_no = fields.Char('DepositorNo', help="YC Debitor Account", default="0000099999")
    partner_no = fields.Char('PartnerNo', help="WAB-CPD-Partner-No", default="0000300999")
    warehouse_id = fields.Char('Plant', help="Warehouse-ID", default="Y999")
    supplier_no = fields.Char('SupplierNo', help="WBL-Supplier-No", default="0000200999")
    email_alarm = fields.Char('Email-Alarm', help="Incident/Alerting Errors", default="Testshop99@Testshop99.com; shopTest95@Testshop99.com")
    sprach_code = fields.Char('Sprachcode', help="e.g. Alert-Message", default="en")
    operating_mode = fields.Selection([('T', 'Integración-Test'),\
        ('P', 'Production'), ('D', 'Development')], default="D", string='Mode', help='Operating Mode')
    soap_url = fields.Selection([('https://service-test.swisspost.ch/apache/yellowcube-test/?wsdl', 'Trial'),\
        ('https://service-test.swisspost.ch/apache/yellowcube-int/?wsdl', 'Integration and aceptance'),\
        ('https://service.swisspost.ch/apache/yellowcube/?wsdl', 'Production')], default="Trial", string='Webservice', help='Selected Webservice')
    certificate_file = fields.Char('Certificate file', help='Certificate file supplied by Yellowcube')
    certificate_key_file = fields.Char('Certificate key file', help='Certificate key file supplied b y Yellowcube')
    certificate_password = fields.Char('Certificate password')

    @api.model
    def get_values(self):
        ICP =self.env['ir.config_parameter'].sudo()
        res = super(ConfigSoapData, self).get_values()
        for param in SOAP_PARAMS:
            value= ICP.get_param('sga_swisspost_soap_connector.{}'.format(param), False)
            res.update({param: value})
        return res

    @api.multi
    def set_values(self):
        super(ConfigSoapData, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        for param in SOAP_PARAMS:
            ICP.set_param('sga_swisspost_soap_connector.{}'.format(param), self[param])
