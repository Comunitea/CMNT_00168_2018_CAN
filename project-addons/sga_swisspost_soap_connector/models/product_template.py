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
from datetime import datetime
from lxml import etree

SOAPENV_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope"
SOAPENV = "{%s}" % SOAPENV_NAMESPACE

ART_NAMESPACE = "https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd"
ART = "{%s}" % ART_NAMESPACE

NSMAP = {'soapenv' : SOAPENV_NAMESPACE, 'art' : ART_NAMESPACE}


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    length = fields.Float()
    width = fields.Float()
    height = fields.Float()
    sga_state = fields.Selection([('integrated', 'Integrated'),\
        ('not-integrated', 'Not Integrated'), ('error', 'Error')], default="not-integrated", string='Sga Status', help='Integration Status')

    def create_soap_xml(self, action='create'):
        # File root
        root = etree.Element(SOAPENV + "Envelope", nsmap=NSMAP)

        # File basics
        header = etree.SubElement(root, SOAPENV + "Header", nsmap=NSMAP)
        body = etree.SubElement(root, SOAPENV + "Body", nsmap=NSMAP)

        # File content
        art = etree.SubElement(body, ART + "ART", nsmap=NSMAP)
        self.file_control_reference(art)
        self.file_article_info(art, action)

        xmlstr = etree.tostring(root, encoding='unicode', method='xml')

        return xmlstr
    
    def file_control_reference(self, art):
        # Art Control Contents
        art_control = etree.SubElement(art, ART + "ControlReference", nsmap=NSMAP)
        etree.SubElement(art_control, ART + "Type", nsmap=NSMAP).text = "ART"
        etree.SubElement(art_control, ART + "Sender", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.sender_id', False)
        etree.SubElement(art_control, ART + "Receiver", nsmap=NSMAP).text = "YELLOWCUBE"
        etree.SubElement(art_control, ART + "Timestamp", nsmap=NSMAP).text = "%s" % datetime.now().strftime("%Y%m%d%H%M%S")
        etree.SubElement(art_control, ART + "OperatingMode", nsmap=NSMAP).text =\
            self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.operating_mode', False)
        etree.SubElement(art_control, ART + "Version", nsmap=NSMAP).text = "1.0"
        etree.SubElement(art_control, ART + "CommType", nsmap=NSMAP).text = "SOAP"
    
    def file_article_info(self, art, changeflag):
        # Art Info
        art_list = etree.SubElement(art, ART + "ArtList", nsmap=NSMAP)
        art_article = etree.SubElement(art_list, ART + "Article", nsmap=NSMAP)

        # Art Data
        if changeflag == 'create':
            etree.SubElement(art_article, ART + "ChangeFlag", nsmap=NSMAP).text = 'I' if self.sga_state == 'not-integrated' else 'U'
        elif changeflag == 'delete':
            etree.SubElement(art_article, ART + "ChangeFlag", nsmap=NSMAP).text = 'D'
        
        etree.SubElement(art_article, ART + "DepositorNo", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.depositor_no', False)
        etree.SubElement(art_article, ART + "PlantID", nsmap=NSMAP).text = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False)
        etree.SubElement(art_article, ART + "ArticleNo", nsmap=NSMAP).text = "%s" % self.default_code # O el self.id
        etree.SubElement(art_article, ART + "BaseUOM", nsmap=NSMAP).text = "PCE" if self.uom_id.name == 'Unit(s)' else "{%s}" % False
        etree.SubElement(art_article, ART + "NetWeight", nsmap=NSMAP, ISO="KGM").text = "%s" % self.weight

        # Art Units of Measure
        art_units = etree.SubElement(art_article, ART + "UnitsOfMeasure", nsmap=NSMAP)
        etree.SubElement(art_units, ART + "EAN", nsmap=NSMAP, EANType="HE").text = "%s" % self.barcode
        etree.SubElement(art_units, ART + "AlternativeUnitISO", nsmap=NSMAP).text = "PCE"
        etree.SubElement(art_units, ART + "AltNumeratorUOM", nsmap=NSMAP).text = "%s" % 1
        etree.SubElement(art_units, ART + "AltDenominatorUOM", nsmap=NSMAP).text = "%s" % 1
        etree.SubElement(art_units, ART + "GrossWeight", nsmap=NSMAP, ISO="KGM").text = "%s" % (self.weight + (self.weight*5)/100)
        etree.SubElement(art_units, ART + "Length", nsmap=NSMAP, ISO="CMT").text = "%s" % self.length or "%s" % 0
        etree.SubElement(art_units, ART + "Width", nsmap=NSMAP, ISO="CMT").text = "%s" % self.width or "%s" % 0
        etree.SubElement(art_units, ART + "Height", nsmap=NSMAP, ISO="CMT").text = "%s" % self.height or "%s" % 0
        etree.SubElement(art_units, ART + "Volume", nsmap=NSMAP, ISO="CMQ").text = "%s" % self.volume or "%s" % 0

        # Art Descriptions
        art_descriptions = etree.SubElement(art_article, ART + "ArticleDescriptions", nsmap=NSMAP)   
        etree.SubElement(art_descriptions, ART + "ArticleDescription", nsmap=NSMAP, ArticleDescriptionLC="de").text = self.description_short
        etree.SubElement(art_descriptions, ART + "ArticleDescription", nsmap=NSMAP, ArticleDescriptionLC="es").text = self.description_short
        etree.SubElement(art_descriptions, ART + "ArticleDescription", nsmap=NSMAP, ArticleDescriptionLC="en").text = self.description_short
    
    def create_soap(self, data_type, operation_type, xml_data):
        soap_connection = self.env['sga_swiss_post_soap'].create({
            'data_type': data_type,
            'operation_type': operation_type,
            'xml_data': xml_data
        })
        return soap_connection

    def send_to_sga(self):
        xml_data = self.create_soap_xml()
        soap_connection = self.create_soap('art', 'send', xml_data)
        res = soap_connection.send()
        if res == True:
            self.sga_state = 'integrated'
        else:
            self.sga_state = 'error'

    def delete_from_sga(self):
        xml_data = self.create_soap_xml('delete')
        soap_connection = self.create_soap('art', 'delete', xml_data)
        res = soap_connection.send()
        if res == True:
            self.sga_state = 'non-integrated'
        else:
            self.sga_state = 'error'