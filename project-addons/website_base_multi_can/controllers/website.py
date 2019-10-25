# -*- coding: utf-8 -*-

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

    def _get_extra_step_multi(self, extra_step):
        if extra_step.multitheme_copy_ids:
            for copy in extra_step.multitheme_copy_ids:
                if copy.website_id and copy.website_id == request.website:
                    return True
        return False

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        """
        Hook to work with extra_option on multi website system.
        """
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=True)
        extra_step = request.env.ref('website_sale.extra_info_option')
        extra_step_multi = self._get_extra_step_multi(extra_step)
        # Check that extra_info option is activated
        if extra_step.active or extra_step_multi:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    # ------------------------------------------------------
    # Extra step
    # ------------------------------------------------------
    @http.route(['/shop/extra_info'], type='http', auth="public", website=True)
    def extra_info(self, **post):
        """
        Hook to work with extra_option on multi website system.
        """
        # Check that this option is activated
        extra_step = request.env.ref('website_sale.extra_info_option')
        extra_step_multi = self._get_extra_step_multi(extra_step)
        if not extra_step.active and not extra_step_multi:
            return request.redirect("/shop/payment")

        # check that cart is valid
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # if form posted
        if 'post_values' in post:
            values = {}
            for field_name, field_value in post.items():
                if field_name in request.env['sale.order']._fields and field_name.startswith('x_'):
                    values[field_name] = field_value
            if values:
                order.write(values)
            return request.redirect("/shop/payment")

        values = {
            'website_sale_order': order,
            'post': post,
            'escape': lambda x: x.replace("'", r"\'"),
            'partner': order.partner_id.id,
            'order': order,
        }

        return request.render("website_sale.extra_info", values)
