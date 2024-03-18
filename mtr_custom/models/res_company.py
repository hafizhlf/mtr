from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    repair_product_id = fields.Many2one(comodel_name='product.product', string='Product')
