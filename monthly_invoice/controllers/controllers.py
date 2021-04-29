# -*- coding: utf-8 -*-
# from odoo import http


# class MonthlyInvoice(http.Controller):
#     @http.route('/monthly_invoice/monthly_invoice/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/monthly_invoice/monthly_invoice/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('monthly_invoice.listing', {
#             'root': '/monthly_invoice/monthly_invoice',
#             'objects': http.request.env['monthly_invoice.monthly_invoice'].search([]),
#         })

#     @http.route('/monthly_invoice/monthly_invoice/objects/<model("monthly_invoice.monthly_invoice"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('monthly_invoice.object', {
#             'object': obj
#         })
