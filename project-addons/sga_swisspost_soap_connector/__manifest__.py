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
{
    'name': 'sga swisspost soap connector',
    'version': '11.0.1.0.0',
    'summary': 'SGA soap website integration for Swisspost',
    'category': 'Custom',
    'author': 'comunitea',
    'website': 'www.comunitea.com',
    'license': 'AGPL-3',
    'depends': [
        'stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config.xml',
        'views/product_template.xml',
        'views/stock_picking_type.xml',
        'views/stock_picking.xml',
        'views/soap_connect.xml',
        'views/stock_warehouse.xml',
        'wizard/save_xml_file.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
