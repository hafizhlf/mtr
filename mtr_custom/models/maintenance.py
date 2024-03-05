from odoo import api, fields, models, tools, _


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    def action_create_repair(self):
        self.env['repair.order'].sudo().create({
            'maintenance_id': self.id,
            'product_id': self.product_id.id,
            'vehicle_id': self.vehicle_id.id,
        })

    def action_view_repairs(self):
        action = self.env.ref('repair.action_repair_order_tree').read()[0]
        action['domain'] = [('maintenance_id', '=', self.id)]
        return action

    def _compute_custom_repair_count(self):
        for main in self:
            custom_repair_count = len(main.repair_ids)
            main.repair_count = custom_repair_count

    name_custom = fields.Char(string='Reference', default=lambda self: self.env['ir.sequence'].next_by_code('maintenance.request'),copy=False, readonly=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Jenis Alat / Kendaraan')
    vehicle_type_id = fields.Many2one(comodel_name='fleet.vehicle.model', string='Type / Merk', related='vehicle_id.model_id')
    no_pol = fields.Char(string='No. Pol / Unit', related='vehicle_id.license_plate')
    estate = fields.Char(string='Estate')
    service = fields.Boolean(string='Service Rutin')
    engine = fields.Boolean(string='Engine System')
    transmision = fields.Boolean(string='Transmision System')
    differential = fields.Boolean(string='Differential System')
    chasis = fields.Boolean(string='Chasis System')
    electric = fields.Boolean(string='Electric System')
    fuel = fields.Boolean(string='Fuel System')
    steering = fields.Boolean(string='Steering System')
    brake = fields.Boolean(string='Brake System')
    cooling = fields.Boolean(string='Cooling System')
    suspension = fields.Boolean(string='Suspension System')
    greasing = fields.Boolean(string='Greasing')
    power = fields.Boolean(string='Power Train System')
    final = fields.Boolean(string='Final Drive System')
    hydroulic = fields.Boolean(string='Hydroulic System')
    carriage = fields.Boolean(string='Under Carriage')
    general = fields.Boolean(string='General Checking')
    others = fields.Boolean(string='Others')
    repair_ids = fields.One2many(comodel_name='repair.order', inverse_name='maintenance_id', string='Repair')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    repair_count = fields.Integer(string="Custom Repair Count", compute="_compute_custom_repair_count")
