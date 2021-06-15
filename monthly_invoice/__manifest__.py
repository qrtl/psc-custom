# Copyright 2021 Quartile Limited
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Monthly Invoice",
    "summary": """
        Module to allow viewing and printing monthly invoices""",
    "license": "LGPL-3",
    "author": "豆ラボ, Quartile Limited",
    "website": "https://beanslabo.com",
    "category": "Accounting",
    "version": "13.0.2.0.0",
    "depends": [
        "crm",
        "sale_stock",
        "report_csv",
        "base_company_reporting",
        "sales_team_attribute",
    ],
    "data": [
        "reports/delivery_note.xml",
        "reports/sale_order.xml",
        "reports/header_custom.xml",
        "reports/ehidden_report.xml",
        "reports/picking_operation.xml",
        "reports/print_format.xml",
        "views/account_move_views.xml",
        "views/delivery_note.xml",
        "views/contact_view_custom.xml",
        "views/sales_order.xml",
        "views/account_invoice_reports.xml",
        "views/report_custom_invoice_templates.xml",
        "views/report_custom_invoice.xml",
    ],
}
