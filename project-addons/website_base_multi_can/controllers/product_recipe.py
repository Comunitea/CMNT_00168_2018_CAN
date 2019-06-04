# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

import ipdb


class RecipeController(http.Controller):
    @http.route(['/recipes'], type='http', auth='public', website=True)
    def get_recipe_list(self):
        recipes = request.env['product.recipe']
        domain = []
        values = {'recipe_list': recipes.search(domain, order='website_sequence desc')}

        # ipdb.set_trace()

        return request.render('website_base_multi_can.page_recipe_list', values)

    @http.route(['/recipes/<path:path>'], type='http', auth='public', website=True)
    def get_one_recipe(self, path):
        recipes = request.env['product.recipe']
        recipe = recipes.search([('slug', '=', path)], limit=1)

        # ipdb.set_trace()

        if recipe:
            values = {'recipe': recipe}
            result = request.render('website_base_multi_can.page_one_recipe', values)
        else:
            result = request.env['ir.http'].reroute('/404')
        return result
