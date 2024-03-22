# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Multi Approval',
    'version': '1.0',
    'category': 'general',
    'summary': 'This module is use for generic and multi level approval',
    'depends': ['purchase_request','purchase'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',        
        'views/approval_configuration.xml',        
        'views/purchase_request.xml',

    ],
    'installable': True,
    'application': True,
}
