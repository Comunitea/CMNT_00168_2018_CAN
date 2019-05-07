# -*- coding: utf-8 -*-

import json
from odoo import http, _
from odoo.osv import expression
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtended(WebsiteSale):

    def _get_search_domain(self, search, category, attrib_values):
        domain = super(WebsiteSaleExtended, self)._get_search_domain(search, category, attrib_values)
        domain = expression.normalize_domain(domain)

        if search:
            domain_search = []
            for srch in search.split(" "):
                domain_search += ['|', '|', '|',
                                  ('public_categ_ids', 'ilike', srch),
                                  ('product_variant_ids', 'ilike', srch),
                                  ('public_categ_ids.public_categ_tag_ids', 'ilike', srch),
                                  ('product_variant_ids.attribute_value_ids', 'ilike', srch)]
            domain = expression.OR([domain, domain_search])

        if category:
            categories = request.env['product.public.category']
            # Search sub-categories of first and second depth level
            sub_cat_l1 = categories.sudo().search([('parent_id', '=', int(category))], order='sequence')
            sub_cat_l2 = categories.sudo().search([('parent_id', 'in', sub_cat_l1.ids)], order='sequence')
            # Create new list of categories to show
            list_cat = [int(category)]
            list_cat.extend(sub_cat_l1.ids)
            list_cat.extend(sub_cat_l2.ids)
            # Search products from sub-categories of first and second depth level
            domain += [('public_categ_ids', 'in', list_cat)]

        return domain
