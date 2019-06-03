# -*- coding: utf-8 -*-
import unicodedata
import re
import random
from odoo import api, fields, models, tools, _


class ProductPublicCategoryTag(models.Model):
    _name = "product.public.category.tag"
    _description = "Website Product Category Related Tag"
    _order = "name"

    name = fields.Char(translate=True)


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    public_categ_tag_ids = fields.Many2many('product.public.category.tag',
                                            'public_categ_tag_rel',
                                            'category_id',
                                            'tag_id',
                                            string='Related Tags',
                                            help="Find Website Categories in Search Box by Related Tags")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    recipe_ids = fields.Many2many('product.recipe', string='Product Recipe',
                                  help=_("Recipes that contains the product"))


class ProductRecipe(models.Model):
    _name = "product.recipe"
    _description = _("Recipe")
    _order = "sequence, title"
    _rec_name = 'title'

    title = fields.Char(_('Title'), index=True, required=True, translate=True)
    subtitle = fields.Char(_('Subtitle'), index=True, required=True, translate=True)
    sequence = fields.Integer(_('Internal Sequence'), default=1,
                              help=_('Gives the sequence order when displaying a recipe list'))
    website_sequence = fields.Integer(_('Website Sequence'), default=lambda self: self._default_website_sequence(),
                                      help=_("Determine the display order in the Website"))
    description = fields.Html(_("Full Description"), strip_style=True, required=True, translate=True)
    description_short = fields.Text(_("Short Description"), help=_("Short Description (Optional)"),
                                    strip_style=True, translate=True)
    product_ids = fields.Many2many('product.template', string='Products',
                                   help=_("Products that contains the recipe"))
    recipe_image_ids = fields.One2many('recipe.image', 'recipe_tmpl_id', string='Images')
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(_("Image"), attachment=True, help=_("This field holds the image used as image for the "
                                                              "recipe, limited to 1024x1024px."))
    image_medium = fields.Binary(_("Medium-sized image"), attachment=True,
                                 help=_("Medium-sized image of the recipe. It is automatically resized as a 128x128px "
                                        "image, with aspect ratio preserved, only when the image exceeds one of "
                                        "those sizes. Use this field in form views or some kanban views."))
    image_small = fields.Binary(_("Small-sized image"), attachment=True,
                                help=_("Small-sized image of the recipe. It is automatically "
                                       "resized as a 64x64px image, with aspect ratio preserved. "
                                       "Use this field anywhere a small image is required."))
    website_published = fields.Boolean(string=_('Published'), default=True,
                                       help=_("Only published recipes are visible on the website"))
    slug = fields.Char(_("Friendly URL"))
    video = fields.Char(_("YouTube video URL"))

    def _default_website_sequence(self):
        self._cr.execute("SELECT MIN(website_sequence) FROM %s" % self._table)
        min_sequence = self._cr.fetchone()[0]
        return min_sequence and min_sequence - 1 or 10

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        slug = vals.get('slug', self.slug)
        if not slug:
            slug = vals.get('title', False) or self.title
        vals.update({'slug': self._slug_validation(slug)})
        super(ProductRecipe, self).write(vals)
        vals.pop('slug')
        return True

    @api.model
    def create(self, vals):
        slug = vals.get('slug', False)
        if not slug or slug == '':
            slug = vals['title']
        vals.update({'slug': self._slug_validation(slug)})
        return super(ProductRecipe, self).create(vals)

    def _slug_validation(self, value):
        # Unicode validation and apply max length
        uni = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub('[\W_]', ' ', uni).strip().lower()
        value = re.sub('[-\s]+', '-', value)
        value = value[:60]
        # Check if this SLUG value already exists in any recipe
        it_exists = self.sudo().search([('slug', '=', value)], limit=1).id
        if it_exists and not it_exists == self.id:
            # Add random URL part
            value = '%s-%d' % (value, random.randint(0, 999))
        return value


class RecipeImage(models.Model):
    _name = 'recipe.image'

    name = fields.Char(_('Name'), translate=True)
    image = fields.Binary(_('Image'), attachment=True)
    recipe_tmpl_id = fields.Many2one('product.recipe', 'Related Recipe', copy=True)
