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

"""
    The signing methods are taken from https://github.com/mvantellingen/python-zeep
"""
from odoo import fields, models, api, _
from zeep import Client, ns
from zeep.cache import SqliteCache
from zeep.utils import detect_soap_env
from zeep.transports import Transport
from zeep.wsse.signature import Signature
from zeep.wsse.username import UsernameToken
from zeep.wsse.utils import ensure_id, get_security_header
from zeep.exceptions import SignatureVerificationFailed
from zeep.plugins import HistoryPlugin
from OpenSSL import crypto
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from lxml import etree
from lxml.etree import QName
import base64
import urllib.request
import ssl
from odoo.http import request
import requests

try:
    import xmlsec
except ImportError:
    xmlsec = None

# SOAP envelope
SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'

import logging.config


#logging.config.dictConfig({
#    'version': 1,
#    'formatters': {
#        'verbose': {
#            'format': '%(name)s: %(message)s'
#        }
#    },
#    'handlers': {
#        'console': {
#            'level': 'DEBUG',
#            'class': 'logging.StreamHandler',
#            'formatter': 'verbose',
#        },
#    },
#    'loggers': {
#        'zeep.transports': {
#            'level': 'DEBUG',
#            'propagate': True,
#            'handlers': ['console'],
#        },
#    }
#})

FILE_NAMES = {
    'wab' : 'YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd',
    'wbl' : 'YellowCube_WBL_REQUEST_SupplierOrders.xsd',
    'art' : 'YellowCube_ART_REQUEST_Artikelstamm.xsd',
    'bar_r' : 'YellowCube_BAR_REQUEST_ArticleList.xsd',
    'bur' : 'YellowCube_BUR_REQUEST_GoodsMovements.xsd',
    'war_r' : 'YellowCube_WAR_REQUEST_GoodsIssueReply.xsd',
    'wba' : 'YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd'
}

def _read_file(f_name):
    with open(f_name, "rb") as f:
        return f.read()

def _make_sign_key(key_data, cert_data, password):
    key = xmlsec.Key.from_memory(key_data, xmlsec.KeyFormat.PEM, password)
    key.load_cert_from_memory(cert_data, xmlsec.KeyFormat.PEM)
    return key

def _make_verify_key(cert_data):
    key = xmlsec.Key.from_memory(cert_data, xmlsec.KeyFormat.CERT_PEM, None)
    return key


class MemorySignature(object):
    """Sign given SOAP envelope with WSSE sig using given key and cert."""

    def __init__(
        self,
        key_data,
        cert_data,
        password=None,
        signature_method=None,
        digest_method=None,
    ):
        check_xmlsec_import()

        self.key_data = key_data
        self.cert_data = cert_data
        self.password = password
        self.digest_method = digest_method
        self.signature_method = signature_method

    def apply(self, envelope, headers):
        key = _make_sign_key(self.key_data, self.cert_data, self.password)
        _sign_envelope_with_key(
            envelope, key, self.signature_method, self.digest_method
        )
        return envelope, headers

    def verify(self, envelope):
        #key = _make_verify_key(self.cert_data)
        #_verify_envelope_with_key(envelope, key)
        return envelope


class Signature(MemorySignature):
    """Sign given SOAP envelope with WSSE sig using given key file and cert file."""

    def __init__(
        self,
        key_file,
        certfile,
        password=None,
        signature_method=None,
        digest_method=None,
    ):
        super(Signature, self).__init__(
            _read_file(key_file),
            _read_file(certfile),
            password,
            signature_method,
            digest_method,
        )


class BinarySignature(Signature):
    """Sign given SOAP envelope with WSSE sig using given key file and cert file.
    Place the key information into BinarySecurityElement."""

    def apply(self, envelope, headers):
        key = _make_sign_key(self.key_data, self.cert_data, self.password)

        _sign_envelope_with_key_binary(
            envelope, key, self.signature_method, self.digest_method
        )
        return envelope, headers


def check_xmlsec_import():
    if xmlsec is None:
        raise ImportError(
            "The xmlsec module is required for wsse.Signature()\n"
            + "You can install xmlsec with: pip install xmlsec\n"
            + "or install zeep via: pip install zeep[xmlsec]\n"
        )


def sign_envelope(
    envelope,
    keyfile,
    certfile,
    password=None,
    signature_method=None,
    digest_method=None,
):
    """Sign given SOAP envelope with WSSE sig using given key and cert.
    Sign the wsu:Timestamp node in the wsse:Security header and the soap:Body;
    both must be present.
    Add a ds:Signature node in the wsse:Security header containing the
    signature.
    Use EXCL-C14N transforms to normalize the signed XML (so that irrelevant
    whitespace or attribute ordering changes don't invalidate the
    signature). Use SHA1 signatures.
    Expects to sign an incoming document something like this (xmlns attributes
    omitted for readability):
    <soap:Envelope>
      <soap:Header>
        <wsse:Security mustUnderstand="true">
          <wsu:Timestamp>
            <wsu:Created>2015-06-25T21:53:25.246276+00:00</wsu:Created>
            <wsu:Expires>2015-06-25T21:58:25.246276+00:00</wsu:Expires>
          </wsu:Timestamp>
        </wsse:Security>
      </soap:Header>
      <soap:Body>
        ...
      </soap:Body>
    </soap:Envelope>
    After signing, the sample document would look something like this (note the
    added wsu:Id attr on the soap:Body and wsu:Timestamp nodes, and the added
    ds:Signature node in the header, with ds:Reference nodes with URI attribute
    referencing the wsu:Id of the signed nodes):
    <soap:Envelope>
      <soap:Header>
        <wsse:Security mustUnderstand="true">
          <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
            <SignedInfo>
              <CanonicalizationMethod
                  Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
              <SignatureMethod
                  Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
              <Reference URI="#id-d0f9fd77-f193-471f-8bab-ba9c5afa3e76">
                <Transforms>
                  <Transform
                      Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                </Transforms>
                <DigestMethod
                    Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                <DigestValue>nnjjqTKxwl1hT/2RUsBuszgjTbI=</DigestValue>
              </Reference>
              <Reference URI="#id-7c425ac1-534a-4478-b5fe-6cae0690f08d">
                <Transforms>
                  <Transform
                      Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                </Transforms>
                <DigestMethod
                    Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                <DigestValue>qAATZaSqAr9fta9ApbGrFWDuCCQ=</DigestValue>
              </Reference>
            </SignedInfo>
            <SignatureValue>Hz8jtQb...bOdT6ZdTQ==</SignatureValue>
            <KeyInfo>
              <wsse:SecurityTokenReference>
                <X509Data>
                  <X509Certificate>MIIDnzC...Ia2qKQ==</X509Certificate>
                  <X509IssuerSerial>
                    <X509IssuerName>...</X509IssuerName>
                    <X509SerialNumber>...</X509SerialNumber>
                  </X509IssuerSerial>
                </X509Data>
              </wsse:SecurityTokenReference>
            </KeyInfo>
          </Signature>
          <wsu:Timestamp wsu:Id="id-7c425ac1-534a-4478-b5fe-6cae0690f08d">
            <wsu:Created>2015-06-25T22:00:29.821700+00:00</wsu:Created>
            <wsu:Expires>2015-06-25T22:05:29.821700+00:00</wsu:Expires>
          </wsu:Timestamp>
        </wsse:Security>
      </soap:Header>
      <soap:Body wsu:Id="id-d0f9fd77-f193-471f-8bab-ba9c5afa3e76">
        ...
      </soap:Body>
    </soap:Envelope>
    """
    # Load the signing key and certificate.
    key = _make_sign_key(_read_file(keyfile), _read_file(certfile), password)
    return _sign_envelope_with_key(envelope, key, signature_method, digest_method)


def _signature_prepare(envelope, key, signature_method, digest_method):
    """Prepare envelope and sign."""
    soap_env = detect_soap_env(envelope)

    # Create the Signature node.
    signature = xmlsec.template.create(
        envelope,
        xmlsec.Transform.EXCL_C14N,
        signature_method or xmlsec.Transform.RSA_SHA1,
    )

    # Add a KeyInfo node with X509Data child to the Signature. XMLSec will fill
    # in this template with the actual certificate details when it signs.
    key_info = xmlsec.template.ensure_key_info(signature)
    x509_data = xmlsec.template.add_x509_data(key_info)
    xmlsec.template.x509_data_add_issuer_serial(x509_data)
    xmlsec.template.x509_data_add_certificate(x509_data)

    # Insert the Signature node in the wsse:Security header.
    security = get_security_header(envelope)
    security.insert(0, signature)

    # Perform the actual signing.
    ctx = xmlsec.SignatureContext()
    ctx.key = key
    _sign_node(ctx, signature, envelope.find(QName(soap_env, "Body")), digest_method)
    timestamp = security.find(QName(ns.WSU, "Timestamp"))
    if timestamp != None:
        _sign_node(ctx, signature, timestamp)
    ctx.sign(signature)

    # Place the X509 data inside a WSSE SecurityTokenReference within
    # KeyInfo. The recipient expects this structure, but we can't rearrange
    # like this until after signing, because otherwise xmlsec won't populate
    # the X509 data (because it doesn't understand WSSE).
    sec_token_ref = etree.SubElement(key_info, QName(ns.WSSE, "SecurityTokenReference"))
    return security, sec_token_ref, x509_data


def _sign_envelope_with_key(envelope, key, signature_method, digest_method):
    _, sec_token_ref, x509_data = _signature_prepare(
        envelope, key, signature_method, digest_method
    )
    sec_token_ref.append(x509_data)


def _sign_envelope_with_key_binary(envelope, key, signature_method, digest_method):
    security, sec_token_ref, x509_data = _signature_prepare(
        envelope, key, signature_method, digest_method
    )
    ref = etree.SubElement(
        sec_token_ref,
        QName(ns.WSSE, "Reference"),
        {
            "ValueType": "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-x509-token-profile-1.0#X509v3"
        },
    )
    bintok = etree.Element(
        QName(ns.WSSE, "BinarySecurityToken"),
        {
            "ValueType": "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-x509-token-profile-1.0#X509v3",
            "EncodingType": "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-soap-message-security-1.0#Base64Binary",
        },
    )
    ref.attrib["URI"] = "#" + ensure_id(bintok)
    bintok.text = x509_data.find(QName(ns.DS, "X509Certificate")).text
    security.insert(1, bintok)
    x509_data.getparent().remove(x509_data)


def verify_envelope(envelope, certfile):
    """Verify WS-Security signature on given SOAP envelope with given cert.
    Expects a document like that found in the sample XML in the ``sign()``
    docstring.
    Raise SignatureVerificationFailed on failure, silent on success.
    """
    key = _make_verify_key(_read_file(certfile))
    return _verify_envelope_with_key(envelope, key)


def _verify_envelope_with_key(envelope, key):

    soap_env = detect_soap_env(envelope)

    header = envelope.find(QName(soap_env, "Header"))
    if header is None:
        raise SignatureVerificationFailed()

    security = header.find(QName(ns.WSSE, "Security"))
    signature = security.find(QName(ns.DS, "Signature"))

    ctx = xmlsec.SignatureContext()

    # Find each signed element and register its ID with the signing context.
    refs = signature.xpath("ds:SignedInfo/ds:Reference", namespaces={"ds": ns.DS})
    for ref in refs:
        # Get the reference URI and cut off the initial '#'
        referenced_id = ref.get("URI")[1:]
        referenced = envelope.xpath(
            "//*[@wsu:Id='%s']" % referenced_id, namespaces={"wsu": ns.WSU}
        )[0]
        ctx.register_id(referenced, "Id", ns.WSU)

    ctx.key = key
    
    try:
        
        ctx.verify(signature)
    except xmlsec.Error:
        # Sadly xmlsec gives us no details about the reason for the failure, so
        # we have nothing to pass on except that verification failed.
        raise SignatureVerificationFailed()


def _sign_node(ctx, signature, target, digest_method=None):
    """Add sig for ``target`` in ``signature`` node, using ``ctx`` context.
    Doesn't actually perform the signing; ``ctx.sign(signature)`` should be
    called later to do that.
    Adds a Reference node to the signature with URI attribute pointing to the
    target node, and registers the target node's ID so XMLSec will be able to
    find the target node by ID when it signs.
    """

    # Ensure the target node has a wsu:Id attribute and get its value.
    node_id = ensure_id(target)

    # Unlike HTML, XML doesn't have a single standardized Id. WSSE suggests the
    # use of the wsu:Id attribute for this purpose, but XMLSec doesn't
    # understand that natively. So for XMLSec to be able to find the referenced
    # node by id, we have to tell xmlsec about it using the register_id method.
    ctx.register_id(target, "Id", ns.WSU)

    # Add reference to signature with URI attribute pointing to that ID.
    ref = xmlsec.template.add_reference(
        signature, digest_method or xmlsec.Transform.SHA1, uri="#" + node_id
    )
    # This is an XML normalization transform which will be performed on the
    # target node contents before signing. This ensures that changes to
    # irrelevant whitespace, attribute ordering, etc won't invalidate the
    # signature.
    xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)

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
            pem = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_file'))
            key = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_key_file'))
            certificate_password = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_password')
            signature = BinarySignature(key, pem, certificate_password)
            history = HistoryPlugin()


            
            if self.data_type == 'art':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"InsertArticleMasterData"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns2:ControlReference", "ART")

                art = self.product_tmpl_id.fileArt(client, "ns2")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.InsertArticleMasterData(controlReference, art)
                    except Exception as e:
                        self.product_tmpl_id.message_post(body="[YELLOWCUBE INTEGRATION]InsertArticleMasterData: {}".format(e))
                        self.response = e
                        return False
                    if history.last_received["envelope"][1][0][4] is not None:
                        response = history.last_received["envelope"][1][0][4]
                    else:
                        response = history.last_received["envelope"][1][0]
                    response_content = etree.tostring(response, encoding="unicode", pretty_print=True)
                    self.product_tmpl_id.message_post(body="[YELLOWCUBE INTEGRATION]InsertArticleMasterData: {}".format(response_content))                   
                    self.response = "[YELLOWCUBE INTEGRATION]InsertArticleMasterData: {}".format(response_content)
                    return True
                
            elif self.data_type == 'wab':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"CreateYCCustomerOrder"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns0:ControlReference", "WAB")

                wab = self.picking_id.fileWab(client, "ns0")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.CreateYCCustomerOrder(controlReference, wab)
                    except Exception as e:
                        self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]CreateYCCustomerOrder: {}".format(e))
                        self.response = e
                        return False
                    if history.last_received["envelope"][1][0][4] is not None:
                        response = history.last_received["envelope"][1][0][4]
                    else:
                        response = history.last_received["envelope"][1][0]
                    response_content = etree.tostring(response, encoding="unicode", pretty_print=True)
                    self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]CreateYCCustomerOrder: {}".format(response_content))                   
                    self.response = "[YELLOWCUBE INTEGRATION]CreateYCCustomerOrder: {}".format(response_content)
                    return True

            elif self.data_type == 'wbl':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"CreateYCSupplierOrder"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns8:ControlReference", "WBL")

                wbl = self.picking_id.fileWbl(client, "ns8")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.CreateYCSupplierOrder(controlReference, wbl)
                    except Exception as e:
                        self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]CreateYCSupplierOrder: {}".format(e))
                        self.response = e
                        return False
                    if history.last_received["envelope"][1][0][4] is not None:
                        response = history.last_received["envelope"][1][0][4]
                    else:
                        response = history.last_received["envelope"][1][0]

                    response_content = etree.tostring(response, encoding="unicode", pretty_print=True)
                    self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]CreateYCSupplierOrder: {}".format(response_content))                   
                    self.response = "[YELLOWCUBE INTEGRATION]CreateYCSupplierOrder: {}".format(response_content)
                    return True
            else:
                raise UserError(_('Data type is not recognized.'))               
            
        else:
            raise UserError(_('Seems that data_type or xml_data are missing.'))

    def get(self):
        
        if self.data_type and self.xml_data:
            url = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.soap_url')
            pem = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_file'))
            key = "../../project-addons/sga_swisspost_soap_connector/static/cert/{}".format(self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_key_file'))
            certificate_password = self.env['ir.config_parameter'].get_param('sga_swisspost_soap_connector.certificate_password')
            signature = BinarySignature(key, pem, certificate_password)
            history = HistoryPlugin()

            if self.data_type == 'bar_r':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetInventory"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns7:ControlReference", "BAR")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.GetInventory(controlReference)
                    except Exception as e:
                        self.response = e
                        return False
                    response_content = etree.tostring(history.last_received["envelope"][1][0], encoding="unicode", pretty_print=True)
                    
                    self.response = response_content
                    return True

            elif self.data_type == 'bur_r':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCGoodsMovements"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns11:ControlReference", "BUR")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.GetYCGoodsMovements(controlReference)
                    except Exception as e:
                        self.response = e
                        return False
                    response_content = etree.tostring(history.last_received["envelope"][1][0], encoding="unicode", pretty_print=True)
                    
                    self.response = response_content
                    return True
                
            elif self.data_type == 'war_r':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCCustomerOrderReply"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns6:ControlReference", "WAR")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.GetYCCustomerOrderReply(controlReference, self.picking_id.name)
                    except Exception as e:
                        self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]GetYCCustomerOrderReply: {}".format(e))
                        self.response = e
                        return False
                    response_content = etree.tostring(history.last_received["envelope"][1][0], encoding="unicode", pretty_print=True)
                    
                    self.response = response_content
                    return True
                
            elif self.data_type == 'wba_r':
                headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': '"GetYCSupplierOrderReply"'}
                transport = Transport(cache=SqliteCache())
                client = Client(wsdl=url, transport=transport, wsse=signature, plugins=[history])

                controlReference = self.controlReference(client, "ns10:ControlReference", "WBA")

                with client.settings(extra_http_headers=headers):
                    try:
                        client.service.GetYCSupplierOrderReply(controlReference, self.picking_id.name)
                    except Exception as e:
                        self.picking_id.message_post(body="[YELLOWCUBE INTEGRATION]GetYCSupplierOrderReply: {}".format(e))
                        self.response = e
                        return False
                    response_content = etree.tostring(history.last_received["envelope"][1][0], encoding="unicode", pretty_print=True)
                    
                    self.response = response_content
                    return True
                
            else:
                raise UserError(_('Data type is not recognized.'))
            
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