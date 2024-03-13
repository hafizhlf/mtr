# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
from odoo import api, fields, Command, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero, float_repr, float_compare, is_html_empty
from odoo.tools.misc import clean_context, format_date

class AccountInherit(models.Model):    
    _inherit = "account.journal"
    
    is_cash_advance = fields.Boolean(string="Is Cash Advance")
    is_report_cash_advance = fields.Boolean(string="Is Report Cash Advance")
    account_ca_debit = fields.Many2one('account.account', string='Account CA Debit')
    account_ca_credit = fields.Many2one('account.account', string='Account CA Credit')
    account_ca_lpj = fields.Many2one('account.account', string='Account LPJ CA')
       
class CashAdvance(models.Model):    
    _name = "cash.advance"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Cash Advance"
    _order = "id desc, id desc"
    _check_company_auto = True
    
    @api.depends('company_id.currency_id')
    def _compute_currency_id(self):
        for sheet in self:
            # Deal with a display bug when there is a company currency change after creation of the expense sheet
            if not sheet.currency_id or sheet.state not in {'post', 'done', 'cancel'}:
                sheet.currency_id = sheet.company_id.currency_id
                
    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _default_bank_journal_id(self):        
        default_company_id = self.default_get(['company_id'])['company_id']
        journal = self.env['account.journal'].search([('is_cash_advance', '=', True), ('company_id', '=', default_company_id)], limit=1)
        return journal
        
    @api.onchange('bank_journal_id')
    def _default_bank_account_id(self):        
        if self.bank_journal_id:
            self.account_id = self.bank_journal_id.account_ca_credit
            self.account_credit_id = self.bank_journal_id.account_ca_debit
        
    @api.depends('account_move_id.payment_state')
    def _compute_payment_state(self):
        for sheet in self:
            sheet.payment_state = sheet.account_move_id.payment_state or 'not_paid'            
    
    name = fields.Char('Document No.', readonly=False, store=True, default='Draft')
    total_amount = fields.Monetary('Total Amount', currency_field='currency_id', store=True, tracking=True)
    
    bank_journal_id = fields.Many2one('account.journal', string='Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, check_company=True, domain="[('is_cash_advance', '=', True), ('company_id', '=', company_id)]",
        default=_default_bank_journal_id, help="The payment method used when the expense is paid by the company.")
    account_id = fields.Many2one('account.account', store=True, readonly=False, string='Account Payable',
        domain="[('account_type', '=', 'asset_cash'),('company_id', '=', company_id)]", help="An account for Cash Advance")
    account_credit_id = fields.Many2one('account.account', store=True, readonly=False, string='Account Receiveable',
        domain="[('account_type', '=', 'asset_receivable'),('company_id', '=', company_id)]", help="An account for Credit")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, tracking=True, states={'draft': [('readonly', False)]}, default=_default_employee_id, check_company=True, domain= lambda self: self.env['hr.expense']._get_employee_id_domain())
    user_id = fields.Many2one('res.users', 'Manager', compute='_compute_from_employee_id', store=True, readonly=True, copy=False, states={'draft': [('readonly', False)]}, tracking=True, domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)])
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["payment_state"].selection,
        string="Payment Status",
        store=True, readonly=True, copy=False, tracking=True, compute='_compute_payment_state')
    expense_report_id = fields.Many2one('hr.expense.sheet', string='Expense Report', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Done'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', states={'draft': [('readonly', False)]},
                                  compute='_compute_currency_id', store=True, readonly=True)
    can_reset = fields.Boolean('Can Reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    approval_date = fields.Datetime('Approval Date', readonly=True)
        
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False, readonly=True)
    
    @api.depends('employee_id')
    def _compute_can_reset(self):
        is_expense_user = self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        for sheet in self:
            sheet.can_reset = is_expense_user if is_expense_user else sheet.employee_id.user_id == self.env.user
    
    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_can_approve(self):
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_team_approver, hr_expense.group_hr_expense_user')
        is_manager = self.user_has_groups('hr_expense.group_hr_expense_manager')
        for sheet in self:
            sheet.can_approve = is_manager or (is_approver and sheet.employee_id.user_id != self.env.user)    
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:            
            vals['name'] = self.env['ir.sequence'].next_by_code('cash.advance')                                    
        
        return super(CashAdvance, self).create(vals_list)
    
    def action_submit_cash_advance(self):
        self.write({'state': 'submit'})        
    
    def _check_can_approve(self):
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id | self.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups('hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                raise UserError(_("You can only approve your department expenses"))
    
    def approve_cash_advance(self):
        self._check_can_approve() 
        self.write({'state': 'approve', 'approval_date': fields.Date.context_today(self)})            
            
    def _do_create_moves(self):                
        create_journal_entries = self.env['account.move'].create({
            'name': '/',
            'ref': self.name,
            'journal_id': self.bank_journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            res = [(0,0, {
                'account_id': self.bank_journal_id.account_ca_debit.id,
                'currency_id': self.currency_id.id,
                'name': "Cash Adv. %s" % ( self.name),                
                'debit': self.total_amount,
                'credit': 0,
            }), (0,0, {
                'account_id': self.account_id.id,
                'currency_id': self.currency_id.id,
                'name': "Cash Adv. %s" % ( self.name),                
                'debit': 0,
                'credit': self.total_amount,
            })]
            create_journal_entries.write({'line_ids': res})
            self.account_move_id = create_journal_entries.id
            create_journal_entries.action_post()    
        
    def action_ca_move_create(self):        
        if any(ca.state != 'approve' for ca in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not ca.bank_journal_id for ca in self):
            raise UserError(_("Specify account journal to generate accounting entries."))

        if not self.employee_id.sudo().address_home_id:
            raise UserError(_("The private address of the employee is required to post the expense report. Please add it on the employee form."))
        
        res = self.with_context(clean_context(self.env.context))._do_create_moves()
        
        self.write({'state': 'done', 'payment_state': 'paid'})
        
        return res
    
    def reset_expense_ca(self):
        if not self.can_reset:
            raise UserError(_("Only HR Officers or the concerned employee can reset to draft."))
        
        self.sudo().write({'state': 'draft', 'approval_date': False})        
        return True
    
    
    def action_unpost(self):
        pass
    
    def reset_expense_sheets(self):
        pass
    
    def action_open_account_move(self):
        self.ensure_one()
        return {
            'name': self.account_move_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[False, "form"]],
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
        }
    
    def action_get_expense_view(self):
        pass
    