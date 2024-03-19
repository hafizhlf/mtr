from odoo import api, fields, models, tools, _


class RepairOrder(models.Model):
    _inherit = "repair.order"

    maintenance_id = fields.Many2one(comodel_name='maintenance.request', string='Maintenance')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Jenis Alat / Kendaraan')
    vehicle_type_id = fields.Many2one(comodel_name='fleet.vehicle.model', string='Type / Merk', related='vehicle_id.model_id')
    no_pol = fields.Char(string='No. Pol / Unit', related='vehicle_id.license_plate')
    approver_1_id = fields.Many2one(comodel_name='res.users', string='Approver 1')
    approver_1_label = fields.Char(string='Approver 1 Label')
    approver_2_id = fields.Many2one(comodel_name='res.users', string='Approver 2')
    approver_2_label = fields.Char(string='Approver 2 Label')


class RepairLine(models.Model):
    _inherit = "repair.line"

    remarks = fields.Char(string='Remarks')
