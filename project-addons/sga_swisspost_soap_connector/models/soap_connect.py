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
from zeep import Client
from zeep.wsse.signature import Signature
from odoo.exceptions import UserError
from lxml import etree
import base64
import urllib.request
import ssl

FILE_NAMES = {
    'wab' : 'YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd',
    'wbl' : 'YellowCube_WBL_REQUEST_SupplierOrders.xsd',
    'art' : 'YellowCube_ART_REQUEST_Artikelstamm.xsd',
    'bar_r' : 'YellowCube_BAR_REQUEST_ArticleList.xsd',
    'bur' : 'YellowCube_BUR_REQUEST_GoodsMovements.xsd',
    'war_r' : 'YellowCube_WAR_REQUEST_GoodsIssueReply.xsd',
    'wba' : 'YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd'
}

class SoapConnect(models.Model):
    _name = 'sga_swiss_post_soap'
    _order = "id DESC"

    data_type = fields.Char('Data type', help="File type")
    operation_type = fields.Char('Operation type', help="Operation type")
    response = fields.Char('Response', help="Response from Web Service")
    xml_data = fields.Text('XML Data')
    model = fields.Char('model')
    picking_id = fields.Many2one('stock.picking', string="Picking")
    product_tmpl_id = fields.Many2one('product.template', string="Product")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    
    def send(self):
        
        validation = self.validate_xml(FILE_NAMES[self.data_type], self.xml_data)
        print(validation)
        if validation != None:
            self.response = validation
            return False            

        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url')
            client = Client(url)
            #key = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_file'))
            #pem = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_key_file'))
            #certificate_password = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_password')
            #client = Client(url, wsse=Signature(key, pem, certificate_password))

            try:
                if self.data_type == 'art':
                    res = client.service.InsertArticleMasterData(self.xml_data)
                elif self.data_type == 'wab':
                    res = client.service.CreateYCCustomerOrder(self.xml_data)
                elif self.data_type == 'wbl':
                    res = client.service.CreateYCSupplierOrder(self.xml_data)
                else:
                    raise UserError(_('Data type is not recognized.'))
                self.response = res
                return True
            except Exception as e:
                print(e)
                self.response = e
                return False
        else:
            raise UserError(_('Seems that data_type or xml_data are missing.'))

    def get(self):
        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url')
            client = Client(url)

            try:

                if self.data_type == 'bar_r':
                    res = client.service.GetInventory()
                elif self.data_type == 'bur':
                    res = client.service.GetYCGoodsMovements()
                elif self.data_type == 'war_r':
                    res = client.service.GetYCCustomerOrderReply()
                elif self.data_type == 'wba':
                    res = client.service.GetYCSupplierOrderReply()
                else:
                    raise UserError(_('Data type is not recognized.'))
                self.response = res
                return True
            
            except Exception as e:
                self.response = e
                return False
            
        else:
            raise UserError(_('Seems that data_type or xml_data are missing.'))

    def validate_xml(self, schema_file, xml_file):

        try:
            #xsd_location = "https://service-test.swisspost.ch/apache/yellowcube-test/%s" % schema_file
            xsd_location = "http://schemas.xmlsoap.org/soap/envelope/"
            name_spaces = {self.data_type: xsd_location}
            curr_tag = ".//%s:%s" % (self.data_type, self.data_type.upper())

            opener = urllib.request.build_opener()
            xsd_doc = etree.parse(opener.open(xsd_location))

            xsd = etree.XMLSchema(xsd_doc)            
            #xml = etree.XML(xml_file).find(curr_tag, namespaces=name_spaces)
            xml = etree.XML(xml_file)
            return xsd.assert_(xml)
        except AssertionError as e:
            return e


    @api.multi
    def save_to_file(self):

        my_file = self.env['save.xml.file.wrd'].create({
            'file_name': '{}.xml'.format(self.data_type),
            'xml_file': base64.b64encode(str.encode(self.xml_data)),
        })

        return {
            'name': _('Download File'),
            'res_id': my_file.id,
            'res_model': 'save.xml.file.wrd',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('sga_swisspost_soap_connector.save_xml_file_wrd_view__done').id,
            'view_mode': 'form',
            'view_type': 'form',
        }