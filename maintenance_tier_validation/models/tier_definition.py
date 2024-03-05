# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    sign_label = fields.Char(string="Sign Label")

    @api.model
    def _get_tier_validation_model_names(self):
        res = super(TierDefinition, self)._get_tier_validation_model_names()
        res.append("maintenance.request")
        return res
