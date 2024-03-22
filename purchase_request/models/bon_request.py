# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]

class BonRequestLine(models.Model):

    _name = "bon.request.line"
    _description = "Bon Request Line"    
    _order = "id desc"

    name = fields.Char(string="Description", tracking=True)
    request_id = fields.Many2one(
        "bon.request",
        string="Purchase Request",
        ondelete="cascade",
        readonly=True,
        index=True        
    )
    company_id = fields.Many2one(        
        related="request_id.company_id",
        string="Company",
        store=True,
    )
    product_id = fields.Many2one(
        "product.product",        
        string="Product"        
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UoM",
        tracking=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_category_id = fields.Many2one(related="product_id.uom_id.category_id")
    product_qty = fields.Float(
        string="Quantity", tracking=True, digits="Product Unit of Measure"
    )
    estimated_cost = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Bon Request Line, not propagated to PR.",
    )
    estimated_total_cost = fields.Monetary(
        currency_field="currency_id",
        default=0.0,        
        help="Estimated cost of Bon Request Line, not propagated to PR.",
    )   
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    
    @api.onchange('estimated_cost','product_qty')
    def _onchange_estimated_total_cost(self):
        if self.estimated_cost:
            self.estimated_total_cost = self.estimated_cost * self.product_qty     


class BonRequest(models.Model):
    _name = "bon.request"
    _description = "Bon Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("bon.request")        

    name = fields.Char(
        string="Request Reference",
        required=True,
        default=lambda self: _("New"),
        tracking=True,
    )    
    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the request.",
        default=fields.Date.context_today,
        tracking=True,
    )
    requested_by = fields.Many2one(
        "res.users",
        required=True,
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        "res.users",
        string="Approver",
        tracking=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("purchase_request.group_purchase_request_manager").id,
            )
        ],
        index=True,
    )
    description = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        required=False,
        default=_company_get,
        tracking=True,
    )
    line_ids = fields.One2many(
        "bon.request.line",
        "request_id",
        string="Products to Purchase",
        readonly=False,
        copy=True,
        tracking=True,
    )    
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )       
    
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    estimated_cost = fields.Monetary(
        compute="_compute_estimated_cost",
        string="Total Estimated Cost",
        store=True,
    )
    
    purchase_request_id = fields.Many2one('purchase.request', string='Purchase Request')

    @api.depends("line_ids")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped("estimated_cost"))    

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update({"state": "draft", "name": self._get_default_name()})
        return super(BonRequest, self).copy(default)

    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._get_default_name()
        requests = super(BonRequest, self).create(vals_list)
        for vals, request in zip(vals_list, requests):
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return requests

    def write(self, vals):
        res = super(BonRequest, self).write(vals)
        for request in self:
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return res

    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete a Order request which is not draft.")
                )
        return super(BonRequest, self).unlink()

    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_to_approve(self):        
        return self.write({"state": "to_approve"})

    def button_approved(self):
        # Create PR
        vals = {
            'requested_by': self.requested_by.id,
            'origin': self.origin,
            'description': self.description,            
        }
        line_vals = []
        for line in self.line_ids:
            line_vals.append((0,0,{
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'estimated_cost': line.estimated_cost,
                'estimated_total_cost': line.estimated_total_cost,
            
            }))
            
        vals.update({'line_ids': line_vals})
        
        pr_id = self.env['purchase.request'].create(vals)
        return self.write({"state": "approved", "purchase_request_id": pr_id.id})

    def button_rejected(self):
        self.mapped("line_ids").do_cancel()
        return self.write({"state": "rejected"})

    def button_done(self):
        return self.write({"state": "done"})
    
    def action_open_purchase_request_view(self):        
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_request.purchase_request_form_action"
        )
        # remove default filters
        action["context"] = {}                                    
        action["views"] = [(self.env.ref("purchase_request.view_purchase_request_form").id, "form")]
        action["res_id"] = self.purchase_request_id.id
        return action