from odoo import api, fields, models, tools, _


class RepairOrder(models.Model):
    _inherit = "repair.order"

    maintenance_id = fields.Many2one(comodel_name='maintenance.request', string='Maintenance')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Jenis Alat / Kendaraan')
    vehicle_type_id = fields.Many2one(comodel_name='fleet.vehicle.model', string='Type / Merk', related='vehicle_id.model_id')
    no_pol = fields.Char(string='No. Pol / Unit', related='vehicle_id.license_plate')


class RepairLine(models.Model):
    _inherit = "repair.line"

    remarks = fields.Char(string='Remarks')
