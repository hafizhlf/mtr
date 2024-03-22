# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
from odoo import api, fields, Command, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero, float_repr, float_compare, is_html_empty
from odoo.tools.misc import clean_context, format_date
from num2words import num2words

class AccountMoveInherit(models.Model):    
    _inherit = "account.move"
    
    @api.depends('needed_terms')
    def _compute_invoice_date_due(self):
        today = fields.Date.context_today(self)
        if self.expense_sheet_id.bank_journal_id.type == 'general':
            for move in self:
                move.invoice_date_due = move.invoice_date_due or today
        else:
            for move in self:
                move.invoice_date_due = move.needed_terms and max(
                    (k['date_maturity'] for k in move.needed_terms.keys() if k),
                    default=False,
                ) or move.invoice_date_due or today
    
    @api.depends('expense_sheet_id')
    def _compute_needed_terms(self):
        # EXTENDS account
        # We want to set the account destination based on the 'payment_mode'.
        if self.expense_sheet_id.bank_journal_id.type == 'general':
            return False 
        super(AccountMoveInherit, self)._compute_needed_terms()   


class HrExpenseInherit(models.Model):    
    _inherit = "hr.expense"
    
    @api.onchange('total_amount')
    def _onchange_total_amount(self):
        if self.total_amount:
            str_amount = num2words(int(self.total_amount), lang='id') + ' Rupiah'            
            self.amount_string = str_amount.title()
                
    number = fields.Char('Document No.', readonly=False, store=True, default='/')
    amount_string = fields.Char('Terbilang', readonly=False, store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:            
            vals['number'] = self.env['ir.sequence'].next_by_code('hr.expense')                                    
        
        return super(HrExpenseInherit, self).create(vals_list) 
    
    
class HrExpenseSheetInherit(models.Model):    
    _inherit = "hr.expense.sheet"
    
    @api.depends('account_move_id.payment_state')
    def _default_account_id(self):
        return self.env.user.employee_id
    
    @api.depends('is_cash_advance','is_custom_expense')
    def _default_domain(self):
        return []
    
    @api.onchange('is_cash_advance','is_custom_expense')    
    def _default_bank_journal_id(self):        
        if not self._context.get('default_is_cash_advance'):
            #company_journal_id = self.env.company.company_expense_journal_id
            #if company_journal_id:
            #    return company_journal_id
            
            default_company_id = self.default_get(['company_id'])['company_id']
            journal = self.env['account.journal'].search([('type', 'in', ['general']), ('company_id', '=', default_company_id)], limit=1)
            return {'value': {'bank_journal_id': journal}, 'domain': {'bank_journal_id': [('type', 'in', ['general']), ('company_id', '=', default_company_id)]}}            
        else:        
            default_company_id = self.default_get(['company_id'])['company_id']
            journal = self.env['account.journal'].search([('is_report_cash_advance', '=', True), ('company_id', '=', default_company_id)], limit=1)
            return {'value': {'bank_journal_id': journal}, 'domain': {'bank_journal_id': [('is_report_cash_advance', '=', True), ('company_id', '=', default_company_id)]}}
    
    number = fields.Char('Document No.', readonly=False, store=True, default='Draft')
    is_cash_advance = fields.Boolean('Is Cash Advance')    
    is_custom_expense = fields.Boolean('Is Custom Expense')
    cash_advance_id = fields.Many2one('cash.advance', string='Cash Advance', states={'done': [('readonly', True)]})
    different_amount = fields.Monetary('Different Amount', currency_field='currency_id', store=True, tracking=True, states={'done': [('readonly', True)]})
    diff_move_id = fields.Many2one('account.move', string='Journal Entry-Back', ondelete='restrict', copy=False, readonly=True, states={'done': [('readonly', True)]})
    
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, domain=_default_domain, check_company=True, help="The payment method used when the expense is paid by the company.")
    
    account_payable_id = fields.Many2one('account.account', string='Account Payable')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:            
            vals['number'] = self.env['ir.sequence'].next_by_code('hr.expense.sheet')                                    
        
        return super(HrExpenseSheetInherit, self).create(vals_list)
    
    def _do_create_custom_expense_moves(self):        
        create_journal_entries = self.env['account.move'].create({
            'ref': self.name,
            'journal_id': self.bank_journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            res = []
            for expense in self.expense_line_ids:
                res.append((0,0, {
                    'account_id': expense.account_id.id,
                    'currency_id': self.currency_id.id,
                    'name': "Expense. %s" % ( self.name),                
                    'debit': expense.total_amount,
                    'credit': 0,
                }))                
            
            res.append((0,0, {
                'account_id': self.account_payable_id.id,
                'currency_id': self.currency_id.id,
                'name': "Bank / Cash %s" % ( self.name),                
                'debit': 0,
                'credit': self.total_amount,
            }))
            create_journal_entries.write({'line_ids': res})
            self.account_move_id = create_journal_entries.id
            create_journal_entries.action_post()
            
        return create_journal_entries
    
    def _do_create_cash_advance_moves(self):        
        create_journal_entries = self.env['account.move'].create({
            'ref': self.name,
            'journal_id': self.bank_journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            res = []
            for expense in self.expense_line_ids:
                res.append((0,0, {
                    'account_id': expense.account_id.id,
                    'currency_id': self.currency_id.id,
                    'name': "Expense. %s" % ( self.name),                
                    'debit': expense.total_amount,
                    'credit': 0,
                }))                
            
            res.append((0,0, {
                'account_id': self.cash_advance_id.account_credit_id.id,
                'currency_id': self.currency_id.id,
                'name': "Cash Adv. %s" % ( self.name),                
                'debit': 0,
                'credit': self.total_amount,
            }))
            create_journal_entries.write({'line_ids': res})
            self.account_move_id = create_journal_entries.id
            create_journal_entries.action_post()
            
        return create_journal_entries
    
    def _do_create_cash_advance_back(self):        
        create_journal_entries = self.env['account.move'].create({
            'ref': '/',
            'journal_id': self.bank_journal_id.id,
            'move_type': 'entry',
        })
        if create_journal_entries:
            res = [(0,0, {
                    'account_id': self.cash_advance_id.account_id.id,
                    'currency_id': self.currency_id.id,
                    'name': "Back - Cash Adv. %s" % ( self.name),                
                    'debit': self.different_amount,
                    'credit': 0,
                }),
                (0,0, {
                'account_id': self.cash_advance_id.account_credit_id.id,
                'currency_id': self.currency_id.id,
                'name': "Back - Cash Adv. %s" % ( self.name),                
                'debit': 0,
                'credit': self.different_amount,
            })]
            create_journal_entries.write({'line_ids': res})
            self.diff_move_id = create_journal_entries.id
            self.cash_advance_id.expense_report_id = self.id            
            
        return create_journal_entries             
    
    def action_sheet_move_create(self):
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            if samples.count(False):
                raise UserError(_("You can't mix sample expenses and regular ones"))
            self.write({'state': 'post'})
            return

        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Specify expense journal to generate accounting entries."))

        if not self.employee_id.sudo().address_home_id:
            raise UserError(_("The private address of the employee is required to post the expense report. Please add it on the employee form."))
        if not self.is_cash_advance and not self.is_custom_expense:
            expense_line_ids = self.mapped('expense_line_ids')\
                .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.company.currency_id).rounding))
            res = expense_line_ids.with_context(clean_context(self.env.context)).action_move_create()
        if self.is_custom_expense:
            res = self.with_context(clean_context(self.env.context))._do_create_custom_expense_moves()
        else:
            res = self.with_context(clean_context(self.env.context))._do_create_cash_advance_moves()

        paid_expenses_company = self.filtered(lambda m: m.payment_mode == 'company_account')
        paid_expenses_company.write({'state': 'done', 'amount_residual': 0.0, 'payment_state': 'paid'})

        paid_expenses_employee = self - paid_expenses_company
        paid_expenses_employee.write({'state': 'post'})
        
        if self.is_cash_advance:
            # Check if amount gain or loss
            self.different_amount = self.cash_advance_id.total_amount - self.total_amount
            if self.different_amount > 0:
                self._do_create_cash_advance_back()                  

        self.activity_update()
        return res
    
    def action_open_account_move(self):
        self.ensure_one()
        if not self.is_cash_advance and not self.is_custom_expense:
            return {
                'name': self.account_move_id.name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[False, "form"]],
                'res_model': 'account.move' if self.payment_mode == 'own_account' else 'account.payment',
                'res_id': self.account_move_id.id if self.payment_mode == 'own_account' else self.account_move_id.payment_id.id,
            }
        else:
            return {
                'name': self.account_move_id.name,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[False, "form"]],
                'res_model': 'account.move',
                'res_id': self.account_move_id.id,
            }
            
    def action_get_difference_view(self):
        self.ensure_one()        
        return {
            'name': self.diff_move_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[False, "form"]],
            'res_model': 'account.move',
            'res_id': self.diff_move_id.id
        }