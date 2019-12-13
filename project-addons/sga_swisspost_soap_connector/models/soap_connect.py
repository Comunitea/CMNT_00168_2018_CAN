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
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.wsse.signature import Signature
from odoo.exceptions import UserError
from datetime import datetime
from lxml import etree
import base64
import urllib.request
import ssl

import logging.config


logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep.transports': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
})

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

    def controlReference(self, client, data_type, ctrl_type):
        try:
            element_type = client.get_element(data_type)
            controlReference = element_type(
                Type=ctrl_type,
                Sender=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.sender_id', False),
                Receiver="YELLOWCUBE",
                Timestamp=datetime.now().strftime("%Y%m%d%H%M%S"),
                OperatingMode=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.operating_mode', False),
                Version=1.0,
                CommType="SOAP"
            )
            return controlReference
        except Exception as e:
            self.response = e
            return False

        
    def send(self):
        
        validation = self.validate_xml(FILE_NAMES[self.data_type], self.xml_data)
        if validation != None:
            self.response = validation
            return False            

        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url') 
            
            #pem = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_file'))
            #key = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_key_file'))
            #certificate_password = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_password')

            try:
                if self.data_type == 'art':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"InsertArticleMasterData"'}
                    transport = Transport(cache=SqliteCache())
                    #client = Client(wsdl=url, transport=transport, wsse=Signature(key, pem, certificate_password))
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns2:ControlReference", "ART")

                    art = self.product_tmpl_id.fileArt(client, "ns2")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.InsertArticleMasterData(controlReference, art)

                        assert res

                        self.response = res
                    
                elif self.data_type == 'wab':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"CreateYCCustomerOrder"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns0:ControlReference", "WAB")

                    wab = self.picking_id.fileWab(client, "ns0")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.CreateYCCustomerOrder(controlReference, wab)

                        assert res

                        self.response = res
                    
                elif self.data_type == 'wbl':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"CreateYCSupplierOrder"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns8:ControlReference", "WBL")

                    wbl = self.picking_id.fileWbl(client, "ns8")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.CreateYCSupplierOrder(controlReference, wbl)

                        assert res

                        self.response = res
                else:
                    raise UserError(_('Data type is not recognized.'))
                self.response = res
                return True
            except Exception as e:
                self.response = e
                return False
        else:
            raise UserError(_('Seems that data_type or xml_data are missing.'))

    def get(self):
        
        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url')

            try:

                if self.data_type == 'bar_r':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetInventory"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns7:ControlReference", "BAR")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.GetInventory(controlReference)

                        assert res

                        self.response = res

                elif self.data_type == 'bur_r':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCGoodsMovements"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns11:ControlReference", "BUR")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.GetYCGoodsMovements(controlReference)

                        assert res

                        self.response = res
                    
                elif self.data_type == 'war_r':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCCustomerOrderReply"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns6:ControlReference", "WAR")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.GetYCCustomerOrderReply(controlReference, self.picking_id.name)

                        assert res

                        self.response = res
                    
                elif self.data_type == 'wba_r':
                    headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCSupplierOrderReply"'}
                    transport = Transport(cache=SqliteCache())
                    client = Client(wsdl=url, transport=transport)

                    controlReference = self.controlReference(client, "ns10:ControlReference", "WBA")

                    with client.settings(extra_http_headers=headers):
                        res = client.service.GetYCSupplierOrderReply(controlReference, self.picking_id.name)

                        assert res

                        self.response = res
                   
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