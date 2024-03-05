from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends('groups_id')
    def _compute_approved_user(self):
        for user in self:
            user.is_approved_user = user.has_group('mtr_custom.group_approved_user')

    @api.depends('groups_id')
    def _compute_applicant_user(self):
        for user in self:
            user.is_applicant_user = user.has_group('mtr_custom.group_applicant_user')

    is_applicant_user = fields.Boolean(compute='_compute_applicant_user', string='Applicant User', store=True)
    is_approved_user = fields.Boolean(compute='_compute_approved_user', string='Approved User', store=True)
