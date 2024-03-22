from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ApprovalUserConfigurationType(models.Model):
    _name = 'approval.user.configuration.type'
    
    name = fields.Char(string='Name', required=True)    

class ApprovalUserConfiguration(models.Model):
    _name = 'approval.user.configuration'
    
    name = fields.Char(string='Name', required=True)
    type = fields.Many2one('approval.user.configuration.type', ondelete='restrict', string='Type', required=True)    
    approval_user_ids = fields.One2many('approval.user.configuration.line', 'approval_id', string='User Name')
    domain_id = fields.Many2one('ir.model', ondelete='cascade', string='Model Applied', required=True)    

    @api.model
    def create(self, vals):
        # validasi double config                    
        res = super(ApprovalUserConfiguration, self).create(vals)
        return res

class ApprovalUserConfigurationLine(models.Model):
    _name = 'approval.user.configuration.line'

    name = fields.Char(string='Name')
    approval_id = fields.Many2one('approval.user.configuration', string='Approval Name')
    user_id = fields.Many2one('hr.employee', string = 'Name')
    user_id_position = fields.Char(string='Postion', related='user_id.job_title')
    sequence = fields.Integer(string='Sequence')