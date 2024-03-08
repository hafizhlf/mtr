from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_approval_time = fields.Integer(related='company_id.auto_approval_time', readonly=False)
