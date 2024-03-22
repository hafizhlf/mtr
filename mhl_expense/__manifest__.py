# -*- coding: utf-8 -*-
{
    'name': "MHL Expense",
    'description': """
        This inherit of MHL Needed
    """,    
    'depends': ['hr_expense'],
    'data': [                
        'data/ir_sequence_data.xml',
        'data/ir.model.access.csv',
        'reports/report_hr_expense_custom.xml',        
        'views/cash_advance_views.xml',
        'views/hr_expense_views.xml',  
        'views/hr_expense_report.xml',                      
    ],    
}
