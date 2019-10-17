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
from datetime import datetime
from lxml import etree

SOAPENV_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope"
SOAPENV = "{%s}" % SOAPENV_NAMESPACE

WAB_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd"
WAB = "{%s}" % WAB_NAMESPACE

WBL_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WBL_REQUEST_SupplierOrders.xsd"
WBL = "{%s}" % WBL_NAMESPACE

NSMAP = {'soapenv' : SOAPENV_NAMESPACE, 'wab' : WAB_NAMESPACE, 'wbl' : WBL_NAMESPACE}


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    sga_state = fields.Selection([('integrated', 'Integrated'), ('waiting', 'Waiting'),\
        ('not-integrated', 'Not Integrated'), ('send-error', 'Send Error'), ('get-error', 'Get Error')],\
            default="not-integrated", string='Sga Status', help='Integration Status')
    sga_integrated = fields.Boolean(related='picking_type_id.sga_integrated')
    sga_integration_type = fields.Selection(related='picking_type_id.sga_integration_type')
    

    def create_soap_xml(self, data_type):
        # File root
        root = etree.Element(SOAPENV + "Envelope", nsmap=NSMAP)

        # File basics
        header = etree.SubElement(root, SOAPENV + "Header", nsmap=NSMAP)
        body = etree.SubElement(root, SOAPENV + "Body", nsmap=NSMAP)

        if data_type == 'wab':
            # Wab file content
            wab = etree.SubElement(body, WAB + "WAB", nsmap=NSMAP)
            self.file_control_reference(wab, data_type)
            self.file_order_info(wab)

        elif data_type == 'wbl':
            # Wbl file content
            wbl = etree.SubElement(body, WBL + "WBL", nsmap=NSMAP)
            self.file_control_reference(wbl, data_type)
            self.file_supplier_order_info(wbl)
        else:
            return False

        xmlstr = etree.tostring(root, encoding='utf8', method='xml')

        return xmlstr
    
    def file_control_reference(self, soap_file, data_type):
        # Control Contents
        control_NS = ''
        if data_type == 'wab':
            control_NS = WAB
        elif data_type == 'wbl':
            control_NS = WBL
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

    def file_supplier_order_info(self, wbl):
        # Wbl Info
        wbl_order = etree.SubElement(wbl, WBL + "SupplierOrder", nsmap=NSMAP)

        # Wbl Order Header
        wbl_order_header = etree.SubElement(wbl_order, WBL + "SupplierOrderHeader", nsmap=NSMAP)
        etree.SubElement(wbl_order_header, WBL + "Plant", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False)
        etree.SubElement(wbl_order_header, WBL + "SupplierNo", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.supplier_no', False)
        etree.SubElement(wbl_order_header, WBL + "SupplierOrderNo", nsmap=NSMAP).text = "%s" % self.name

        # Wbl Supplier Order Detail
        wbl_order_positions = etree.SubElement(wbl_order, WBL + "SupplierOrderPositions", nsmap=NSMAP) # Revisar si es SupplierOrderDetail o SupplierOrderPositions. El pdf viene como Detail y el xsd viene positions

        for move_line in self.move_line_ids:
            wbl_position = etree.SubElement(wbl_order_positions, WBL + "Position", nsmap=NSMAP)
            etree.SubElement(wbl_position, WBL + "PosNo", nsmap=NSMAP).text = "%s" % move_line.id[-6:]
            etree.SubElement(wbl_position, WBL + "ArticleNo", nsmap=NSMAP).text = "%s" % move_line.product_id.default_code # O el id, según lo que pongas en product_template
            etree.SubElement(wbl_position, WBL + "EAN", nsmap=NSMAP).text = "%s" % move_line.product_id.barcode
            etree.SubElement(wbl_position, WBL + "Quantity", nsmap=NSMAP).text = "%s" % move_line.qty_done
            etree.SubElement(wbl_position, WBL + "QuantityISO", nsmap=NSMAP).text = "PCE"
            etree.SubElement(wbl_position, WBL + "PosText", nsmap=NSMAP).text = "%s" % move_line.product_id.description_short

    def file_order_info(self, wab):
        # Wab Info
        wab_order = etree.SubElement(wab, WAB + "Order", nsmap=NSMAP)
        wab_order_header = etree.SubElement(wab_order, WAB + "OrderHeader", nsmap=NSMAP)
        
        etree.SubElement(wab_order_header, WAB + "DepositorNo", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.depositor_no', False)
        etree.SubElement(wab_order_header, WAB + "CustomerOrderNo", nsmap=NSMAP).text = "%s" % self.name
        etree.SubElement(wab_order_header, WAB + "CustomerOrderDate", nsmap=NSMAP).text = "%s" % datetime.strptime(self.sale_id.confirmation_date, '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d")

        ## Wab partner address
        wab_partner_adress = etree.SubElement(wab_order, WAB + "PartnerAdress", nsmap=NSMAP)
        wab_partner = etree.SubElement(wab_partner_adress, WAB + "Partner", nsmap=NSMAP)
        etree.SubElement(wab_partner, WAB + "PartnerType", nsmap=NSMAP).text = "WE"
        etree.SubElement(wab_partner, WAB + "PartnerNo", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.partner_no', False)
        etree.SubElement(wab_partner, WAB + "PartnerReference", nsmap=NSMAP).text = "%s" % self.name
        etree.SubElement(wab_partner, WAB + "Title", nsmap=NSMAP).text = ""
        etree.SubElement(wab_partner, WAB + "Name1", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[:35]
        etree.SubElement(wab_partner, WAB + "Name2", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[36:70]
        etree.SubElement(wab_partner, WAB + "Name3", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[71:136]
        etree.SubElement(wab_partner, WAB + "Name4", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.state_id.name # name4/additional address line
        etree.SubElement(wab_partner, WAB + "Street", nsmap=NSMAP).text = "%s, %s" % (self.sale_id.partner_shipping_id.street, self.sale_id.partner_shipping_id.street2)
        etree.SubElement(wab_partner, WAB + "CountryCode", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.country_id.code
        etree.SubElement(wab_partner, WAB + "ZIPCode", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.zip
        etree.SubElement(wab_partner, WAB + "City", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.city
        etree.SubElement(wab_partner, WAB + "POBox", nsmap=NSMAP).text = ""
        etree.SubElement(wab_partner, WAB + "PhoneNo", nsmap=NSMAP).text = "%s" % self.partner_id.phone
        etree.SubElement(wab_partner, WAB + "MobileNo", nsmap=NSMAP).text = "%s" % self.partner_id.mobile
        etree.SubElement(wab_partner, WAB + "SMSAvisMobNo", nsmap=NSMAP).text = "%s" % self.partner_id.mobile
        etree.SubElement(wab_partner, WAB + "FaxNo", nsmap=NSMAP).text = ""
        etree.SubElement(wab_partner, WAB + "Email", nsmap=NSMAP).text = "%s" % self.partner_id.email
        etree.SubElement(wab_partner, WAB + "LanguageCode", nsmap=NSMAP).text = "%s" % self.partner_id.lang if self.partner_id.lang in ['de', 'fr', 'it', 'en'] else "en"

        ## Wab additional services
        wab_added_services = etree.SubElement(wab_order, WAB + "ValueAddedServices", nsmap=NSMAP)
        wab_additional_service = etree.SubElement(wab_added_services, WAB + "AdditionalService", nsmap=NSMAP)
        etree.SubElement(wab_additional_service, WAB + "BasicShippingService", nsmap=NSMAP).text = "PRI" # Preguntar qué servicio de la tabla usa
        etree.SubElement(wab_additional_service, WAB + "AdditionalShippingService", nsmap=NSMAP).text = "" # Preguntar si necesitan más servicios
        etree.SubElement(wab_additional_service, WAB + "DeliveryInstructions", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "FloorNo", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "NotificationType", nsmap=NSMAP).text = "4" # 1- TEL, 2-FAX, 3-SMS, 4-EMAIL
        etree.SubElement(wab_additional_service, WAB + "NotificationServiceCode", nsmap=NSMAP).text = "2" # 0-On delivery, 1-24h, 2-On validation, 256-Saturday, 257-Evening 
        etree.SubElement(wab_additional_service, WAB + "DelveryDate", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DelveryTimeJIT", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DelveryTimeFrom", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DelveryTimeTo", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DelveryTimePeriodeCode", nsmap=NSMAP).text = "3" # 1-morning, 2-afternoon, 3-both
        etree.SubElement(wab_additional_service, WAB + "DelveryLocation", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "CODAmount", nsmap=NSMAP).text = "" # Cash on delivery amount
        etree.SubElement(wab_additional_service, WAB + "CODAccountNo", nsmap=NSMAP).text = "" # Cash on delivery account number
        etree.SubElement(wab_additional_service, WAB + "CODRefNo", nsmap=NSMAP).text = "" # Cash on delivery ISR reference
        etree.SubElement(wab_additional_service, WAB + "FrightShippingFlag", nsmap=NSMAP).text = "0" # Cash on delivery ISR reference
        
        # Wab order positions
        wab_order_positions = etree.SubElement(wab_order, WAB + "OrderPositions", nsmap=NSMAP)
        
        for move_line in self.move_line_ids:
            wab_position = etree.SubElement(wab_order_positions, WAB + "Position", nsmap=NSMAP)
            etree.SubElement(wab_position, WAB + "PosNo", nsmap=NSMAP).text = "%s" % move_line.id[-6:]
            etree.SubElement(wab_position, WAB + "ArticleNo", nsmap=NSMAP).text = "%s" % move_line.product_id.default_code # O el id, según lo que pongas en product_template
            etree.SubElement(wab_position, WAB + "EAN", nsmap=NSMAP).text = "%s" % move_line.product_id.barcode
            etree.SubElement(wab_position, WAB + "YCLot", nsmap=NSMAP).text = ""
            etree.SubElement(wab_position, WAB + "Lot", nsmap=NSMAP).text = "%s" % self.name
            etree.SubElement(wab_position, WAB + "Plant", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False)
            etree.SubElement(wab_position, WAB + "Quantity", nsmap=NSMAP, ISO="PCE").text = "%s" % move_line.qty_done
            etree.SubElement(wab_position, WAB + "ShortDescription", nsmap=NSMAP).text = "%s" % move_line.product_id.description_short
            etree.SubElement(wab_position, WAB + "PickingMessage", nsmap=NSMAP).text = ""
            etree.SubElement(wab_position, WAB + "PickingMessageLC", nsmap=NSMAP).text = "en"
            etree.SubElement(wab_position, WAB + "ReturnReason", nsmap=NSMAP).text = ""

        # Wab order documents
        # Mirar cómo adjuntar los pdf
        wab_order_documents = etree.SubElement(wab_order, WAB + "OrderDocuments", nsmap=NSMAP, OrderDocumentsFlag="1") # 1-Yes, 2-No
        wab_order_filename = etree.SubElement(wab_order_documents, WAB + "OrderDocFilenames", nsmap=NSMAP)
        etree.SubElement(wab_order_filename, WAB + "OrderDocFilename", nsmap=NSMAP).text = "Order - %s.pdf" % self.sale_id.name
    
    def create_soap(self, data_type, operation_type, xml_data):
        soap_connection = self.env['sga_swiss_post_soap'].create({
            'data_type': data_type,
            'operation_type': operation_type,
            'xml_data': xml_data
        })
        return soap_connection

    def send_to_sga(self):
        if self.sga_integrated and self.sga_integration_type == 'sga_swiss_post':
            data_type = self.picking_type_id.swiss_soap_file
            print(data_type)
            xml_data = self.create_soap_xml(data_type)
            soap_connection = self.create_soap(data_type, 'send', xml_data)
            res = soap_connection.send()
            if res == True:
                self.sga_state = 'waiting'
            else:
                self.sga_state = 'send-error'