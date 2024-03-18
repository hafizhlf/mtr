from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = ["maintenance.request", "tier.validation"]
    _state_from = ["draft", "pending"]

    _tier_validation_manual_config = False

    state = fields.Selection([
        ('draft', 'New Request'),
        ('pending', 'Pending'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel'),
        ], string='Approval Status', default="draft", copy=False, index=True)

    @api.constrains('stage_id')
    def _constraint_stage_id(self):
        for rec in self:

            if rec.state == 'pending':
                raise ValidationError(_("You can only change the stage when the request have been approved."))

    def _compute_state(self):
        for rec in self:
            context = {'skip_validation_check': True}
            if rec._calc_reviews_validated(rec.review_ids):
                rec.with_context(context).write({'state': 'confirm'})

    def request_validation(self):
        res = super().request_validation()
        self.write({'state': 'pending'})
        return res

    def validate_tier(self):
        res = super().validate_tier()
        self._compute_state()
        return res

    def reject_tier(self):
        res = super().reject_tier()
        context = {'skip_validation_check': True}
        self.with_context(context).archive_equipment_request()
        return res

    def archive_equipment_request(self):
        super().archive_equipment_request()
        self.write({'state': 'cancel'})

    def reset_equipment_request(self):
        super().reset_equipment_request()
        self.write({'state': 'draft'})

    @api.model
    def auto_inprogress_status_maintenance_request(self):
        company = self.env.company
        odoobot = self.env.ref("base.partner_root")
        context = {'skip_validation_check': True}
        resource_calendar = company.resource_calendar_id

        if not resource_calendar:
            return
        
        work_days = self._get_work_days(resource_calendar)
        if not work_days or company.auto_approval_time < 1:
            return
        
        now = fields.Datetime.now()
        schedule_date = fields.Datetime.from_string(now)
        if schedule_date.strftime('%w') in str(work_days):
            request_date = now - timedelta(days=company.auto_approval_time)
            orders_to_confirm = self.search([('write_date', '<=', request_date)])

            for order in orders_to_confirm:
                order.with_context(context).write({'state': 'confirm'})
                message = _("Maintenance request has been automatically approved by %s as the maintenance record exceeds %s days.") % (odoobot.display_name, company.auto_approval_time)
                order.message_post(body=message)

    def _get_work_days(self, resource_calendar):
        work_days = [
            int(attendance.dayofweek) + 1
            for attendance in resource_calendar.attendance_ids
            if isinstance(attendance.dayofweek, str) and attendance.dayofweek.isdigit()
        ]
        work_days = [day % 7 for day in work_days]
        return list(set(work_days))
