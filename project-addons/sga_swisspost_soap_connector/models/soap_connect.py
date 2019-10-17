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
from suds.client import Client
from odoo.exceptions import UserError

class SoapConnect(models.Model):
    _name = 'sga_swiss_post_soap'

    data_type = fields.Char('Data type', help="File type")
    operation_type = fields.Char('Operation type', help="Operation type")
    response = fields.Char('Response', help="Response from Web Service")
    xml_data = fields.Text('XML Data')

    
    def send(self):
        print(self.xml_data)
        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url')
            client = Client(url)

            try:
                if self.data_type == 'art':
                    res = client.service.InsertArticleMasterData(self.xml_data)
                elif self.data_type == 'wab':
                    print("lel")
                    res = client.service.CreateYCCustomerOrder(self.xml_data)
                    print(res)
                elif self.data_type == 'wbl':
                    res = client.service.CreateYCSupplierOrder(self.xml_data)
                else:
                    raise UserError(_('Data type is not recognized.'))
                print("res")
                print(res)
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
            client = Client(url)
            print(client)

            if self.data_type == 'bar':
                res = client.service.GetInventory()
            elif self.data_type == 'bur':
                res = client.service.GetYCGoodsMovements()
            elif self.data_type == 'war':
                res = client.service.GetYCCustomerOrderReply()
            elif self.data_type == 'wba':
                res = client.service.GetYCSupplierOrderReply()
            else:
                raise UserError(_('Data type is not recognized.'))
            
            print(res)
            return res
        else:
            raise UserError(_('Seems that data_type or xml_data are missing.'))