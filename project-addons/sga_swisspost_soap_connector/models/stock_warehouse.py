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
#    MERCHANTABILITY or FITNESS FOR A PWABICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models, api, _
from lxml import etree
from datetime import datetime
from odoo.exceptions import ValidationError

SOAPENV_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
SOAPENV = "{%s}" % SOAPENV_NAMESPACE

BAR_R_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd"
BUR_R_NAMESPACE = "https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd"
BAR_R = "{%s}" % BAR_R_NAMESPACE

BUR_R = "{%s}" % BUR_R_NAMESPACE

NSMAP = {'soapenv' : SOAPENV_NAMESPACE, 'bar_r' : BAR_R_NAMESPACE, 'bur_r' : BUR_R_NAMESPACE}

class StockWarehouseSGA(models.Model):

    _inherit = "stock.warehouse"

    sga_integrated = fields.Boolean('Sga', help='Marcar si tiene un tipo de integración con el sga')
    sga_integration_type = fields.Selection([('sga_swiss_post', 'Swiss POST')], 'Integration type')
    last_synchronization = fields.Char('Last Synchronization')
    sga_state = fields.Selection([('integrated', 'Integrated'), ('waiting', 'Waiting'),\
        ('not-integrated', 'Not Integrated'), ('send-error', 'Send Error'), ('get-error', 'Get Error')],\
            default="not-integrated", string='Sga Status', help='Integration Status')

    @api.constrains('sga_integration_type')
    def _check_sga_swiss_post_integration(self):
        active_warehouses = self.env['stock.warehouse'].search([('sga_integrated', '=', True), ('sga_integration_type', '=', 'sga_swiss_post')\
            , ('id', '!=', self.id)])
        if active_warehouses:
            raise ValidationError(_("There is already a warehouse connected to the Swiss Post SOAP"))

    def create_soap(self, data_type, operation_type, xml_data):
        soap_connection = self.env['sga_swiss_post_soap'].create({
            'data_type': data_type,
            'operation_type': operation_type,
            'xml_data': xml_data,
            'model': 'stock.warehouse',
            'warehouse_id': self.id
        })
        return soap_connection

    def create_soap_xml(self, data_type):
        # File root
        root = etree.Element(SOAPENV + "Envelope", nsmap=NSMAP)

        # File basics
        header = etree.SubElement(root, SOAPENV + "Header", nsmap=NSMAP)
        body = etree.SubElement(root, SOAPENV + "Body", nsmap=NSMAP)

        if data_type == 'bar_r':
            # Wab file content
            bar_r = etree.SubElement(body, BAR_R + "BAR_R", nsmap=NSMAP)
            self.file_control_reference(bar_r, data_type)
        
        elif data_type == 'bur_r':
            # Wab file content
            bur_r = etree.SubElement(body, BUR_R + "BUR_R", nsmap=NSMAP)
            self.file_control_reference(bur_r, data_type)

        else:
            return False

        xmlstr = etree.tostring(root, encoding='utf8', method='xml')

        return xmlstr

    def file_control_reference(self, soap_file, data_type):
        # Control Contents
        control_NS = ''
        if data_type == 'bar_r':
            control_NS = BAR_R
        if data_type == 'bur_r':
            control_NS = BUR_R
        else:
            return False

        soap_file_control = etree.SubElement(soap_file, control_NS + "ControlReference", nsmap=NSMAP)
        etree.SubElement(soap_file_control, control_NS + "Type", nsmap=NSMAP).text = "%s" % data_type.upper()
        etree.SubElement(soap_file_control, control_NS + "Sender", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.sender_id', False)
        etree.SubElement(soap_file_control, control_NS + "Receiver", nsmap=NSMAP).text = "YELLOWCUBE"
        etree.SubElement(soap_file_control, control_NS + "Timestamp", nsmap=NSMAP).text = "%s" % datetime.now().strftime("%Y%m%d%H%M%S")
        etree.SubElement(soap_file_control, control_NS + "OperatingMode", nsmap=NSMAP).text =\
            self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.operating_mode', False)
        etree.SubElement(soap_file_control, control_NS + "Version", nsmap=NSMAP).text = "1.0"
        etree.SubElement(soap_file_control, control_NS + "CommType", nsmap=NSMAP).text = "SOAP"
        etree.SubElement(soap_file_control, control_NS + "TransControlID", nsmap=NSMAP, UniqueFlag="1").text = "%s" % self.id
        etree.SubElement(soap_file_control, control_NS + "TransMaxWait", nsmap=NSMAP).text = "3600"

    @api.multi
    def inventory_synchronization(self):
        for warehouse in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post'):
            xml_data = warehouse.create_soap_xml('bar_r')
            soap_connection = warehouse.create_soap('bar_r', 'get', xml_data)
            res = soap_connection.get()
            if res == True:
                warehouse.sga_state = 'waiting'
            else:
                warehouse.sga_state = 'get-error'


    @api.multi
    def inventory_movements(self):
        for warehouse in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post'):
            xml_data = warehouse.create_soap_xml('bur_r')
            soap_connection = warehouse.create_soap('bur_r', 'get', xml_data)
            res = soap_connection.get()