# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_users_ids = fields.One2many('purchase.request.approval_line','purchase_request_id', string='Approval Status')
    approval_id = fields.Many2one('approval.user.configuration', string='Approval Type', domain=[('domain_id','=','purchase.request')])
    
    def button_to_approve(self):
        if self.approval_users_ids:
            for record in self.approval_users_ids:
                self.update({
                    'approval_users_ids': [(2, record.id)]
                })
        #aprroval_configuration = self.env['approval.user.configuration'].sudo().search([('domain_id','=','purchase.request')])
        for user in self.approval_id.approval_user_ids:
            self.update({
                'approval_users_ids': [(0, 0, {
                    'purchase_request_id':self.id ,
                    'user_id' : user.user_id.id,
                    'sequence': user.sequence
                })],
            })
        res = super(PurchaseRequest, self).button_to_approve()
        return res

class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.approval_line'

    purchase_request_id = fields.Many2one('purchase.request', string='Approval Request Purchase Order', ondelete='cascade')
    user_id = fields.Many2one('hr.employee', string = 'Name')
    user_id_position = fields.Char(string='Postion', related='user_id.job_title')
    sequence = fields.Integer(string='Sequence')
    sequence_ref = fields.Integer('No.', compute="_sequence_ref")
    state = fields.Selection([('waiting','Waiting for Approval ...'),
                              ('approved','Approved'),
                              ('rejected','Rejected')], default='waiting')

    @api.depends('purchase_request_id.approval_users_ids', 'purchase_request_id.approval_users_ids.user_id')
    def _sequence_ref(self):
        for line in self:
            no = 0
            sorted_list = line.purchase_request_id.approval_users_ids.sorted((lambda o: o.sequence))
            for l in sorted_list:
                no += 1
                l.sequence_ref = no

    
    def validation_approval_user(self):
        if self.purchase_request_id.state not in ['to_approve']:
            raise UserError('Please Validate This document first')
            
        if not self.sudo().user_id.user_id:
            raise UserError(_('Please Contact administrator to create related user'))
        elif self.sudo().user_id.user_id == self.env.user:
            # if self.sequence != 0:
            sorted_list = self.sudo().purchase_request_id.approval_users_ids.sorted((lambda o: o.sequence_ref))
            # for user in self.sudo().purchase_request_id.approval_users_ids:
            for user in sorted_list:
                if not user.state and user.sequence_ref < self.sequence_ref:
                    raise UserError(_('Users %s still not response this document yet.') % (user.user_id.name))
            return True
        else:
            if not self.env.user.has_group('multi_approval.group_bypass_multiapproval'):
                raise UserError(_('Users %s cannot responses to approval user %s.') % (self.env.user.name, self.sudo().user_id.resource_id.name))
    
    def get_before_receiver_status(self):
        # Exception for ref = 1
        if self.sequence_ref != 1:
            sequnce_before_user = int(self.sequence_ref - 1)
            line_ids = self.env['purchase.request.approval_line'].sudo().search([('purchase_request_id','=', self.purchase_request_id.id)])
            for line in line_ids:            
                if line.sequence_ref == sequnce_before_user:
                    if line.state not in ['rejected','approved']:
                        return False
                    else:
                        return True
        else:
            return True
                
    
    def get_next_reciever(self):
        # sequnce_next_user = int(self.sequence_ref + 1)
        sequnce_next_user = int(self.sequence_ref + 1)
        line_ids = self.env['purchase.request.approval_line'].sudo().search([('purchase_request_id','=', self.purchase_request_id.id)])
        for line in line_ids:
            # if user.sequence_ref == sequnce_next_user:
            #     return user.user_id
            if line.sequence_ref == sequnce_next_user:
                return line.user_id

    def action_approved(self):
        if self.purchase_request_id.state == 'draft':
            raise UserError(_('Please Confirm Order first Purchase Order before approving the document'))        
        # Check if user is valid to confirm this document        
        self.validation_approval_user()
        
        # Check if statu before approval has been confirmed
        if not self.get_before_receiver_status():
            raise UserError(_('Please check for your BEFORE APPROVER to approve the document.'))
        
        next_reciever = self.get_next_reciever()
        if next_reciever:    
            pass
        else:
            # LOGIC
            pr_id = self.env['purchase.request'].sudo().search([('id','=', self.purchase_request_id.id)])
            pr_id.button_approved()
        self.state = 'approved'

    def action_rejected(self):              
        self.validation_approval_user()
        
        # Check if statu before approval has been confirmed
        if not self.get_before_receiver_status():
            raise UserError(_('Please check for your BEFORE APPROVER to approve the document.'))
                
        self.state = 'rejected'
        return self.purchase_request_id.button_rejected()