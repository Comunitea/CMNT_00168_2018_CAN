# -*- coding: utf-8 -*-
#
# © 2018 Comunitea
# Pavel Smirnov <pavel@comunitea.com>
# Rubén Seijas <ruben@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################
#
#    Copyright (C) {year} {company} All Rights Reserved
#    ${developer} <{mail}>$
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
    'name': 'Theme Canilike',
    'version': '1.0',
    'summary': 'Frontend Customization for Canilike Website',
    'description': '',
    'category': 'Theme',
    'author': 'Comunitea',
    'website': 'http://www.comunitea.com',
    'license': 'AGPL-3',
    'contributors': [
        'Pavel Smirnov <pavel@comunitea.com>',
        'Rubén Seijas <ruben@comunitea.com>',
        'Vicente Gutiérrez <vicente@comunitea.com>',
    ],
    'depends': [
        'website_base_multi_can',
        'website_custom_geoip',
    ],
    'data': [
        'data/theme_data.xml',
        'data/website_data.xml',
        'data/legal_data.xml',
        'data/menu_data.xml',
        'templates/head.xml',
        'templates/header.xml',
        'templates/footer.xml',
        'templates/product.xml',
        'templates/cookies.xml',
        'templates/checkout.xml',
        'templates/page_aboutus.xml',
        'templates/page_contactus.xml',
        'templates/page_home.xml',
        'templates/page_payment.xml',
        'templates/pages.xml',
        'views/customize_views.xml',
    ],
    'images': [
        '/static/description/icon.png',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
}
