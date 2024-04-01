# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from random import randint

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, is_html_empty, clean_context


class Repair(models.Model):
    _name = 'repair.order'
    _inherit = ['repair.order', "tier.validation"]
    _state_from = ["under_repair"]
    _state_to = ["done"]

    _tier_validation_manual_config = False

    def validate_tier(self):
        res = super().validate_tier()
        context_action = {'skip_validation_check': True}
        self.with_context(context_action).action_repair_end()
        return res
