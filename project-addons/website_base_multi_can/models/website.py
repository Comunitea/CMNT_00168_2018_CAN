# -*- coding: utf-8 -*-
#
# © 2018 Comunitea - Ruben Seijas <ruben@comunitea.com>
# © 2018 Comunitea - Pavel Smirnov <pavel@comunitea.com>
#
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http, api, models, fields
from odoo.http import request
from odoo.addons.seo_base.models.settings import _default_website


class Website(models.Model):
    _inherit = 'website'

    social_twitter = fields.Char(related=False, store=True)
    social_facebook = fields.Char(related=False, store=True)
    social_github = fields.Char(related=False, store=True)
    social_linkedin = fields.Char(related=False, store=True)
    social_youtube = fields.Char(related=False, store=True)
    social_googleplus = fields.Char(related=False, store=True)
    social_instagram = fields.Char(string='Instagram Account')
    email = fields.Char(string='Website Email')
    phone = fields.Char(string='Website Phone')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_id = fields.Many2one('website', string="website", default=_default_website, required=True)
    social_instagram = fields.Char(related='website_id.social_instagram')
    email = fields.Char(related='website_id.email')
    phone = fields.Char(related='website_id.phone')


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    not_public = fields.Boolean(string='Available only for logged users', default=False)
    not_portal = fields.Boolean(string='Available only for public users', default=False)
    website_published = fields.Boolean(string='Published', default=True)
