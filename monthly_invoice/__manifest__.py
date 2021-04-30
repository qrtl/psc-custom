# -*- coding: utf-8 -*-
{
    'name': "Monthly Invoice",

    'summary': """
        Module to allow viewing and printing monthly invoices""",

    'description': """
        
    """,

    'author': "豆ラボ",
    'website': "https://beanslabo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.0.1.14.5',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'account', 'sale', 'stock', 'sale_stock', 'report_csv'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/monthly_invoices.xml',
        'views/sales_order.xml',
        'views/delivery_note.xml',
        'views/contact_view_custom.xml',
        'reports/monthly_invoice.xml',
        'reports/delivery_note.xml',
        'reports/sale_order.xml',
        'reports/header_custom.xml',
        'reports/ehidden_report.xml',
        'reports/invoice.xml',
        'reports/picking_operation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}
