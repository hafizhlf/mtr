from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    repair_product_id = fields.Many2one(related='company_id.repair_product_id', readonly=False)
