# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class RecipeController(http.Controller):

    @http.route(['/recipes'], type='http', auth='public', website=True)
    def get_recipe_list(self):
        recipes = request.env['product.recipe']
        domain = []
        values = {'recipe_list': recipes.search(domain, order='website_sequence desc')}
        return request.render('website_base_multi_can.recipes_list_template', values)

    @http.route(['/recipe/<path:path>'], type='http', auth='public', website=True)
    def get_one_recipe(self, path):
        recipes = request.env['product.recipe']
        recipe = recipes.search([('slug', '=', path)], limit=1)
        if recipe:
            values = {'recipe': recipe}
            result = request.render('website_base_multi_can.recipe_template', values)
        else:
            result = request.env['ir.http'].reroute('/404')
        return result
