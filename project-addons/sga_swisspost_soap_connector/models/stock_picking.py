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
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from odoo.exceptions import UserError
import base64

SOAPENV_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
SOAPENV = "{%s}" % SOAPENV_NAMESPACE

WAB_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd"
WAB = "{%s}" % WAB_NAMESPACE

WBL_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WBL_REQUEST_SupplierOrders.xsd"
WBL = "{%s}" % WBL_NAMESPACE

WAR_R_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WBL_REQUEST_SupplierOrders.xsd"
WAR_R = "{%s}" % WAR_R_NAMESPACE

WBA_R_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_WBL_REQUEST_SupplierOrders.xsd"
WBA_R = "{%s}" % WBA_R_NAMESPACE

NSMAP = {'soapenv' : SOAPENV_NAMESPACE, 'wab' : WAB_NAMESPACE, 'wbl' : WBL_NAMESPACE, 'war_r': WAR_R_NAMESPACE, 'wba_r': WBA_R_NAMESPACE}


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    sga_state = fields.Selection([('integrated', 'Integrated'), ('waiting', 'Waiting'),\
        ('not-integrated', 'Not Integrated'), ('send-error', 'Send Error'), ('get-error', 'Get Error'), ('confirmed', 'Confirmed'),\
             ('confirmation-error', 'Confirmation Error')], default="not-integrated", string='Sga Status', help='Integration Status')
    sga_integrated = fields.Boolean(related='picking_type_id.sga_integrated')
    sga_integration_type = fields.Selection(related='picking_type_id.sga_integration_type')


    def fileWbl(self, client, prefix):

        try:

            #Elements
            iso_element = client.get_element("{}:QuantityISO".format(prefix))
            order_element = client.get_element("{}:SupplierOrder".format(prefix))
            orderHeader_element = client.get_element("{}:SupplierOrderHeader".format(prefix))
            orderPositions_element = client.get_element("{}:SupplierOrderPositions".format(prefix))
            position_element = client.get_element("{}:Position".format(prefix))

            #Values
            iso = iso_element("KGM")


            ## OrderHeader

            orderHeader = orderHeader_element(
                DepositorNo=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.depositor_no', False),
                Plant=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False),
                SupplierNo=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.supplier_no', False),
                SupplierOrderNo=self.name.replace('/', '_')
            )


            # OrderPositions

            positions_arrary = []

            for move_line in self.move_line_ids:

                position = position_element(
                    PosNo=move_line.id,
                    ArticleNo=move_line.product_id.default_code, # O el id, según lo que pongas en product_template
                    Quantity=move_line.product_uom_qty,
                    QuantityISO=iso,
                    PosText=move_line.with_context(lang='de_DE').product_id.name[:40],
                )
                
                positions_arrary.append(position)
                    
            orderPositions = orderPositions_element(
                Position = positions_arrary
            )

            order = order_element(
                SupplierOrderHeader=orderHeader,
                SupplierOrderPositions=orderPositions
            )

            return order
        
        except Exception as e:
            return e


    def fileWab(self, client, prefix):

        try:

            #Types
            iso_type = client.get_type("{}:ISO".format(prefix))

            #Elements
            order_element = client.get_element("{}:Order".format(prefix))
            orderHeader_element = client.get_element("{}:OrderHeader".format(prefix))
            partnerAddress_element = client.get_element("{}:PartnerAddress".format(prefix))
            partner_element = client.get_element("{}:Partner".format(prefix))
            orderPositions_element = client.get_element("{}:OrderPositions".format(prefix))
            position_element = client.get_element("{}:Position".format(prefix))
            orderDocuments_element = client.get_element("{}:OrderDocuments".format(prefix))
            orderDocFilenames_element = client.get_element("{}:OrderDocFilenames".format(prefix))
            orderDocFilename_element = client.get_element("{}:OrderDocFilename".format(prefix))
            docType_element = client.get_element("{}:DocType".format(prefix))
            docMimeType_element = client.get_element("{}:DocMimeType".format(prefix))
            docStream_element = client.get_element("{}:DocStream".format(prefix))
            valueAddedServices_element = client.get_element("{}:ValueAddedServices".format(prefix))
            additionalService_element = client.get_element("{}:AdditionalService".format(prefix))

            #Values
            iso = iso_type("KGM")


            ## OrderHeader

            orderHeader = orderHeader_element(
                DepositorNo=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.depositor_no', False),
                CustomerOrderNo=self.name.replace('/', '_'),
                CustomerOrderDate=datetime.strptime(self.sale_id.confirmation_date, '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d")
            )


            ## PartnerAddress

            partner = partner_element(
                PartnerType="WE",
                PartnerNo=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.partner_no', False),
                PartnerReference=self.name.replace('/', '_'),
                Title="",
                Name1=self.sale_id.partner_shipping_id.name[:35],
                Name2=self.sale_id.partner_shipping_id.name[36:70],
                Name3=self.sale_id.partner_shipping_id.name[71:136],
                Name4=self.sale_id.partner_shipping_id.state_id.name if self.sale_id.partner_shipping_id.state_id.name else '', # name4/additional address line
                Street="%s, %s" % (self.sale_id.partner_shipping_id.street, self.sale_id.partner_shipping_id.street2),
                CountryCode=self.sale_id.partner_shipping_id.country_id.code,
                ZIPCode=self.sale_id.partner_shipping_id.zip,
                City=self.sale_id.partner_shipping_id.city,
                POBox="",
                PhoneNo=self.partner_id.phone,
                MobileNo=self.partner_id.mobile if self.partner_id.mobile else '',
                SMSAvisMobNo=self.partner_id.mobile if self.partner_id.mobile else '',
                FaxNo="",
                Email=self.partner_id.email,
                LanguageCode=self.partner_id.lang if self.partner_id.lang in ['de', 'fr', 'it', 'en'] else "en"
            )

            partnerAddress = partnerAddress_element(
                Partner=partner
            )


            # ValueAddedService
            
            AdditionalService = additionalService_element(
                BasicShippingServices="PRI", # Preguntar qué servicio de la tabla usa
                AdditionalShippingServices="", # Preguntar si necesitan más servicios
                DeliveryInstructions="",
                FloorNo="",
                NotificationType="4", # 1- TEL, 2-FAX, 3-SMS, 4-EMAIL
                NotificationServiceCode="2", # 0-On delivery, 1-24h, 2-On validation, 256-Saturday, 257-Evening 
                DeliveryDate="",
                DeliveryTimeJIT="",
                DeliveryTimeFrom="",
                DeliveryTimeTo="",
                DeliveryPeriodeCode="3",  # 1-morning, 2-afternoon, 3-both
                DeliveryLocation="",
                CODAmount="", # Cash on delivery amount
                CODAccountNo="", # Cash on delivery account number
                CODRefNo="", # Cash on delivery ISR reference
                FrightShippingFlag="0" # Cash on delivery ISR reference
            )

            valueAddedServices = valueAddedServices_element(
                AdditionalService=AdditionalService
            )


            # OrderPositions

            positions_arrary = []

            for move_line in self.move_line_ids:

                position = position_element(
                    PosNo=move_line.id,
                    ArticleNo=move_line.product_id.default_code, # O el id, según lo que pongas en product_template
                    EAN=move_line.product_id.barcode if move_line.product_id.barcode else '',
                    YCLot="",
                    Lot=self.name,
                    Plant=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False),
                    Quantity=move_line.product_uom_qty,
                    QuantityISO=iso,
                    ShortDescription=move_line.with_context(lang='de_DE').product_id.name[:40],
                    PickingMessage="",
                    PickingMessageLC="en",
                    ReturnReason=""
                )
                
                positions_arrary.append(position)
                    
            orderPositions = orderPositions_element(
                Position = positions_arrary
            )


            # OrderDocuments        

            pdf = self.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([self.sale_id.id])[0] or False

            orderDocFilename = orderDocFilename_element(
                "Order - %s.pdf" % self.sale_id.name
            )

            orderDocFilenames = orderDocFilenames_element(
                OrderDocFilename=orderDocFilename
            )      

            orderDocuments = orderDocuments_element(
                OrderDocFilenames = orderDocFilenames
            )

            if pdf:

                orderDocuments.OrderDocumentsFlag=1 # 1-Yes, 0-No

                docType = docType_element(
                    "IV"
                )

                docMimeType = docMimeType_element(
                    'pdf'
                )

                docStream = docStream_element(
                    base64.b64encode(pdf)
                )

                orderDocuments.Docs = {docType, docMimeType, docStream}

            else:
                orderDocuments.OrderDocumentsFlag=0 # 1-Yes, 0-No

            order = order_element(
                OrderHeader=orderHeader,
                PartnerAddress=partnerAddress,
                ValueAddedServices=valueAddedServices,
                OrderPositions=orderPositions,
                OrderDocuments=orderDocuments
            )

            return order
        
        except Exception as e:
            return e
    

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

        elif data_type == 'war_r':
            # Wbl file content
            war_r = etree.SubElement(body, WAR_R + "WAR_R", nsmap=NSMAP)
            self.file_control_reference(war_r, data_type)
            self.request_order_info_info(war_r, data_type)
        
        elif data_type == 'wba_r':
            # Wbl file content
            wba_r = etree.SubElement(body, WBA_R + "WBA_R", nsmap=NSMAP)
            self.file_control_reference(wba_r, data_type)
            self.request_order_info_info(wba_r, data_type)
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
        elif data_type == 'war_r':
            control_NS = WAR_R
        elif data_type == 'wba_r':
            control_NS = WBA_R
        else:
            return False

        soap_file_control = etree.SubElement(soap_file, control_NS + "ControlReference", nsmap=NSMAP)
        etree.SubElement(soap_file_control, control_NS + "Type", nsmap=NSMAP).text = "%s" % data_type.replace('_r', '').upper()
        etree.SubElement(soap_file_control, control_NS + "Sender", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.sender_id', False)
        etree.SubElement(soap_file_control, control_NS + "Receiver", nsmap=NSMAP).text = "YELLOWCUBE"
        etree.SubElement(soap_file_control, control_NS + "Timestamp", nsmap=NSMAP).text = "%s" % datetime.now().strftime("%Y%m%d%H%M%S")
        etree.SubElement(soap_file_control, control_NS + "OperatingMode", nsmap=NSMAP).text =\
            self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.operating_mode', False)
        etree.SubElement(soap_file_control, control_NS + "Version", nsmap=NSMAP).text = "1.0"
        etree.SubElement(soap_file_control, control_NS + "CommType", nsmap=NSMAP).text = "SOAP"
        etree.SubElement(soap_file_control, control_NS + "TransControlID", nsmap=NSMAP, UniqueFlag="1").text = "%s" % self.id
        etree.SubElement(soap_file_control, control_NS + "TransMaxWait", nsmap=NSMAP).text = "3600"
    
    def request_order_info_info(self, soap_file, data_type):
        # Order info request
        if data_type == 'war_r':
            etree.SubElement(soap_file, WAR_R + "CustomerOrderNo", nsmap=NSMAP).text = "%s" % self.name.replace('/', '_')
        elif data_type == 'wba_r':
            etree.SubElement(soap_file, WBA_R + "SupplierOrderNo", nsmap=NSMAP).text = "%s" % self.name.replace('/', '_')

    def file_supplier_order_info(self, wbl):
        # Wbl Info
        wbl_order = etree.SubElement(wbl, WBL + "SupplierOrder", nsmap=NSMAP)

        # Wbl Order Header
        wbl_order_header = etree.SubElement(wbl_order, WBL + "SupplierOrderHeader", nsmap=NSMAP)
        etree.SubElement(wbl_order_header, WBL + "Plant", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False)
        etree.SubElement(wbl_order_header, WBL + "SupplierNo", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.supplier_no', False)
        etree.SubElement(wbl_order_header, WBL + "SupplierOrderNo", nsmap=NSMAP).text = "%s" % self.name.replace('/', '_')

        # Wbl Supplier Order Detail
        wbl_order_positions = etree.SubElement(wbl_order, WBL + "SupplierOrderPositions", nsmap=NSMAP) # Revisar si es SupplierOrderDetail o SupplierOrderPositions. El pdf viene como Detail y el xsd viene positions

        for move_line in self.move_line_ids:
            wbl_position = etree.SubElement(wbl_order_positions, WBL + "Position", nsmap=NSMAP)
            etree.SubElement(wbl_position, WBL + "PosNo", nsmap=NSMAP).text = "%s" % move_line.id
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
        etree.SubElement(wab_order_header, WAB + "CustomerOrderNo", nsmap=NSMAP).text = "%s" % self.name.replace('/', '_')
        etree.SubElement(wab_order_header, WAB + "CustomerOrderDate", nsmap=NSMAP).text = "%s" % datetime.strptime(self.sale_id.confirmation_date, '%Y-%m-%d %H:%M:%S').strftime("%Y%m%d")

        ## Wab partner address
        wab_partner_adress = etree.SubElement(wab_order, WAB + "PartnerAdress", nsmap=NSMAP)
        wab_partner = etree.SubElement(wab_partner_adress, WAB + "Partner", nsmap=NSMAP)
        etree.SubElement(wab_partner, WAB + "PartnerType", nsmap=NSMAP).text = "WE"
        etree.SubElement(wab_partner, WAB + "PartnerNo", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.partner_no', False)
        etree.SubElement(wab_partner, WAB + "PartnerReference", nsmap=NSMAP).text = "%s" % self.name.replace('/', '_')
        etree.SubElement(wab_partner, WAB + "Title", nsmap=NSMAP).text = ""
        etree.SubElement(wab_partner, WAB + "Name1", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[:35]
        etree.SubElement(wab_partner, WAB + "Name2", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[36:70]
        etree.SubElement(wab_partner, WAB + "Name3", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.name[71:136]
        etree.SubElement(wab_partner, WAB + "Name4", nsmap=NSMAP).text = "%s" % self.sale_id.partner_shipping_id.state_id.name if self.sale_id.partner_shipping_id.state_id.name else '' # name4/additional address line
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
        etree.SubElement(wab_additional_service, WAB + "DeliveryDate", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DeliveryTimeJIT", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DeliveryTimeFrom", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DeliveryTimeTo", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "DeliveryPeriodeCode", nsmap=NSMAP).text = "3" # 1-morning, 2-afternoon, 3-both
        etree.SubElement(wab_additional_service, WAB + "DeliveryLocation", nsmap=NSMAP).text = ""
        etree.SubElement(wab_additional_service, WAB + "CODAmount", nsmap=NSMAP).text = "" # Cash on delivery amount
        etree.SubElement(wab_additional_service, WAB + "CODAccountNo", nsmap=NSMAP).text = "" # Cash on delivery account number
        etree.SubElement(wab_additional_service, WAB + "CODRefNo", nsmap=NSMAP).text = "" # Cash on delivery ISR reference
        etree.SubElement(wab_additional_service, WAB + "FrightShippingFlag", nsmap=NSMAP).text = "0" # Cash on delivery ISR reference
        
        # Wab order positions
        wab_order_positions = etree.SubElement(wab_order, WAB + "OrderPositions", nsmap=NSMAP)

        ctx = self._context.copy()
        ctx.update(lang='de_DE')
        
        for move_line in self.move_line_ids:
            wab_position = etree.SubElement(wab_order_positions, WAB + "Position", nsmap=NSMAP)
            etree.SubElement(wab_position, WAB + "PosNo", nsmap=NSMAP).text = "%s" % move_line.id
            etree.SubElement(wab_position, WAB + "ArticleNo", nsmap=NSMAP).text = "%s" % move_line.product_id.default_code # O el id, según lo que pongas en product_template
            etree.SubElement(wab_position, WAB + "EAN", nsmap=NSMAP).text = "%s" % move_line.product_id.barcode
            etree.SubElement(wab_position, WAB + "YCLot", nsmap=NSMAP).text = ""
            etree.SubElement(wab_position, WAB + "Lot", nsmap=NSMAP).text = "%s" % self.name
            etree.SubElement(wab_position, WAB + "Plant", nsmap=NSMAP).text = "%s" % self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False)
            etree.SubElement(wab_position, WAB + "Quantity", nsmap=NSMAP, ISO="PCE").text = "%s" % move_line.product_uom_qty
            etree.SubElement(wab_position, WAB + "ShortDescription", nsmap=NSMAP).text = "%s" % move_line.with_context(ctx).product_id.name
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
            'xml_data': xml_data,
            'model': 'stock.picking',
            'picking_id': self.id
        })
        return soap_connection

    @api.multi
    def send_to_sga(self):
        for picking in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post'):
            data_type = picking.picking_type_id.swiss_soap_file
            xml_data = picking.create_soap_xml(data_type)
            soap_connection = picking.create_soap(data_type, 'send', xml_data)
            res = soap_connection.send()
            if res == True:
                picking.sga_state = 'waiting'
            else:
                picking.sga_state = 'send-error'

    @api.multi
    def get_from_sga(self):
        #for picking in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post' and sga_state == 'waiting'):
        for picking in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post'):
            if picking.picking_type_id.code == 'outgoing':
                data_type = 'war_r'
            elif picking.picking_type_id.code == 'incoming':
                data_type = 'wba_r'
            else:
                return False
            xml_data = picking.create_soap_xml(data_type)
            soap_connection = picking.create_soap(data_type, 'get', xml_data)
            res = soap_connection.get()
            # Mirar si es necesario WEA
            #if res == True and data_type == 'war_r':
            #    picking.sga_state = 'integrated'
            #elif res == True and data_type == 'wba_r':
            #    picking.sga_state = 'confirmed'
            if res == True:
                picking.sga_state = 'integrated'
            else:
                picking.sga_state = 'get-error'
    
    # WEA no se aplica en SOAP ?

    #def confirm_to_sga(self):
    #    if self.sga_integrated and self.sga_integration_type == 'sga_swiss_post' and sga_state == 'confirmed':
    #        data_type = 'wea'
    #        xml_data = self.create_soap_xml(data_type)
    #        soap_connection = self.create_soap(data_type, 'send', xml_data)
    #        res = soap_connection.get()
    #        if res == True:
    #            self.sga_state = 'confirmed'
    #        else:
    #            self.sga_state = 'get-error'