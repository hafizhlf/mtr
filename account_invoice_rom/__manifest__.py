# -*- coding: utf-8 -*-
{
    'name': "Account Invoice Sequence Romawi",

    'summary': """This module is used for custom romawi sequence romawi and format Invoice""",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['base', 'account','product','sale'],
    'data': [        
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'views/account_move_views.xml',
        'views/templates_invoices_format.xml',
        'views/templates.xml',
    ],    
}
