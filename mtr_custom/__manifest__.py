{
    'name': 'MTR Custom Module',
    'summary': 'Custom module for managing PT. MTR flow',
    'description': """
        This module customizes Odoo to implement the PT. MTR flow.
        It includes models, views, and business logic tailored to PT. MTR.
    """,
    'version': '1.0',
    'category': 'Uncategorized', 
    'author': 'Secret', 
    'depends': [
        'maintenance',
        'repair',
        'base_tier_validation',
        'maintenance_tier_validation',
        'fleet',
        'sign',
    ],
    'data': [
        'data/sequence.xml',
        'security/security.xml',
        'views/maintenance_views.xml',
        'views/repair_views.xml',
        'report/maintenance_report.xml',
        'report/repair_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
