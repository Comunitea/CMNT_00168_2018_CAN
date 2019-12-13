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
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport

SOAPENV_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
SOAPENV = "{%s}" % SOAPENV_NAMESPACE

ART_NAMESPACE = "https://service-test.swisspost.ch/apache/yellowcube-test/YellowCube_ART_REQUEST_Artikelstamm.xsd"
ART = "{%s}" % ART_NAMESPACE

NSMAP = {'soapenv' : SOAPENV_NAMESPACE, 'art' : ART_NAMESPACE}


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    length = fields.Float()
    width = fields.Float()
    height = fields.Float()
    sga_state = fields.Selection([('integrated', 'Integrated'),\
        ('not-integrated', 'Not Integrated'), ('error', 'Error')], default="not-integrated", string='Sga Status', help='Integration Status')
    sga_integration_type = fields.Selection([('sga_swiss_post', 'Swiss POST')], 'Integration type')
    sga_integrated = fields.Boolean('Sga', help='Marcar si tiene un tipo de integración con el sga')


    def fileArt(self, client, prefix):

        try:
            #Types
            iso_type = client.get_type("{}:ISO".format(prefix))
            float13v3mandatory_type = client.get_type("{}:Float13v3Mandatory".format(prefix))
            float13v3_type = client.get_type("{}:Float13v3".format(prefix))
            descriptionlc_type = client.get_type("{}:ArticleDescription".format(prefix))

            #Elements
            units_element = client.get_element("{}:UnitsOfMeasure".format(prefix))
            description_element = client.get_element("{}:ArticleDescription".format(prefix))
            descriptions_element = client.get_element("{}:ArticleDescriptions".format(prefix))
            article_element = client.get_element("{}:Article".format(prefix))
            articleList_element = client.get_element("{}:ArticleList".format(prefix))

            #Values
            iso = iso_type("KGM")
            grossWeight_qty = float13v3_type("{:.2f}".format(self.weight + (self.weight*5)/100))
            weight = float13v3mandatory_type("{:.2f}".format(self.weight + (self.weight*5)/100))
            articleDescription_de = descriptionlc_type(self.with_context(lang='de_DE').name[:40])
            

            unitsOfMeasure = units_element(
                EAN=self.barcode if self.barcode else '',
                AlternateUnitISO="PCE",
                AltNumeratorUOM=1,
                AltDenominatorUOM=1,
                GrossWeight=grossWeight_qty,
                Length="%s" % self.length or "%s" % 0,
                Width="%s" % self.width or "%s" % 0,
                Height="%s" % self.height or "%s" % 0,
                Volume="%s" % self.volume or "%s" % 0,
            )

            unitsOfMeasure.EAN.EANType="HE"
            unitsOfMeasure.GrossWeight.ISO=iso
            unitsOfMeasure.Length.ISO=iso
            unitsOfMeasure.Width.ISO=iso
            unitsOfMeasure.Height.ISO=iso
            unitsOfMeasure.Volume.ISO=iso
            
            articleDescription = description_element(
                articleDescription_de,
                ArticleDescriptionLC="de"
            )    

            articleDescriptions = descriptions_element(
                ArticleDescription=articleDescription
            )

            article = article_element(
                ChangeFlag='I' if self.sga_state == 'not-integrated' else 'U',
                DepositorNo=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.depositor_no', False),
                PlantID=self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.warehouse_id', False),
                ArticleNo="%s" % self.default_code or self.id,
                BaseUOM="PCE",
                NetWeight=weight,
                BatchMngtReq=1,
                MinRemLife="",
                PeriodExpDateType="",
                SerialNoFlag=0,
                UnitsOfMeasure=unitsOfMeasure,
                ArticleDescriptions=articleDescriptions
            )

            article.NetWeight.ISO=iso

            articleList = articleList_element(Article=article)

            return articleList
        except Exception as e:
            return e

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
        etree.SubElement(art_article, ART + "ArticleNo", nsmap=NSMAP).text = "%s" % self.default_code or self.id
        etree.SubElement(art_article, ART + "BaseUOM", nsmap=NSMAP).text = "PCE"
        etree.SubElement(art_article, ART + "NetWeight", nsmap=NSMAP, ISO="KGM").text = "%s" % self.weight

        # Art Units of Measure
        art_units = etree.SubElement(art_article, ART + "UnitsOfMeasure", nsmap=NSMAP)
        etree.SubElement(art_units, ART + "EAN", nsmap=NSMAP, EANType="HE").text = "%s" % self.barcode or ''
        etree.SubElement(art_units, ART + "AlternateUnitISO", nsmap=NSMAP).text = "PCE"
        etree.SubElement(art_units, ART + "AltNumeratorUOM", nsmap=NSMAP).text = "%s" % 1
        etree.SubElement(art_units, ART + "AltDenominatorUOM", nsmap=NSMAP).text = "%s" % 1
        etree.SubElement(art_units, ART + "GrossWeight", nsmap=NSMAP, ISO="KGM").text = "%s" % (self.weight + (self.weight*5)/100)
        etree.SubElement(art_units, ART + "Length", nsmap=NSMAP, ISO="CMT").text = "%s" % self.length or "%s" % 0
        etree.SubElement(art_units, ART + "Width", nsmap=NSMAP, ISO="CMT").text = "%s" % self.width or "%s" % 0
        etree.SubElement(art_units, ART + "Height", nsmap=NSMAP, ISO="CMT").text = "%s" % self.height or "%s" % 0
        etree.SubElement(art_units, ART + "Volume", nsmap=NSMAP, ISO="CMQ").text = "%s" % self.volume or "%s" % 0

        # Art Descriptions
        art_descriptions = etree.SubElement(art_article, ART + "ArticleDescriptions", nsmap=NSMAP)
        ctx = self._context.copy()
        ctx.update(lang='de_DE')
        etree.SubElement(art_descriptions, ART + "ArticleDescription", nsmap=NSMAP, ArticleDescriptionLC="de").text = self.with_context(ctx).name
        ctx.update(lang='en_EN')
        etree.SubElement(art_descriptions, ART + "ArticleDescription", nsmap=NSMAP, ArticleDescriptionLC="en").text = self.with_context(ctx).name
    
    def create_soap(self, data_type, operation_type, xml_data):
        soap_connection = self.env['sga_swiss_post_soap'].create({
            'data_type': data_type,
            'operation_type': operation_type,
            'xml_data': xml_data,
            'model': 'product.template',
            'product_tmpl_id': self.id
        })
        return soap_connection

    @api.multi
    def send_to_sga(self):
        for product in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post'):
            xml_data = product.create_soap_xml()
            soap_connection = product.create_soap('art', 'send', xml_data)
            res = soap_connection.send()
            if res == True:
                product.sga_state = 'integrated'
            else:
                product.sga_state = 'error'

    @api.multi
    def delete_from_sga(self):
        for product in self.filtered(lambda x: x.sga_integrated and x.sga_integration_type == 'sga_swiss_post' and x.sga_state == 'integrated'):
            xml_data = product.create_soap_xml('delete')
            soap_connection = product.create_soap('art', 'delete', xml_data)
            res = soap_connection.send()
            if res == True:
                product.sga_state = 'non-integrated'
            else:
                product.sga_state = 'error'