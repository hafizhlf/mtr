from odoo import fields, models


class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'

    hm_value = fields.Float('Hourmeter Value')
