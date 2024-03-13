from odoo import api, fields, models, _
from collections import defaultdict


class AccountJournal(models.Model):
    _inherit = 'account.journal'
        
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Sequence',
        store=True        
    ) 


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        def journal_key(move):
            return (move.journal_id, move.journal_id.refund_sequence and move.move_type)

        def date_key(move):
            return (move.date.year, move.date.month)

        grouped = defaultdict(  # key: journal_id, move_type
            lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                lambda: {
                    'records': self.env['account.move'],
                    'format': False,
                    'format_values': False,
                    'reset': False
                }
            )
        )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            journal = self.env['account.journal'].browse(vals.get('journal_id'))
            if vals.get('name') == '/' and self._context.get('default_move_type') == 'out_invoice':
                if self.journal_id.sequence_id:            
                    vals['name'] = journal.sequence_id.next_by_code(journal.sequence_id.code)
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('account.move')                
            if journal.sequence_id:            
                vals['name'] = journal.sequence_id.next_by_code(journal.sequence_id.code)            
        
        return super(AccountMove, self).create(vals_list)
    
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    discount_amount = fields.Float(
        string='Discount in Amount',
        digits='Discount',
        default=0.0,
        compute='_compute_totals', store=True
    )
    
    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id','discount_amount')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit
            discount_amount = line.quantity * (line.price_unit - line_discount_price_unit)
            
            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
                line.discount_amount = discount_amount
            else:
                line.price_total = line.price_subtotal = subtotal
                line.discount_amount = discount_amount