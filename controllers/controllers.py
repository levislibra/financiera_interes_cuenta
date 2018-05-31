# -*- coding: utf-8 -*-
from openerp import http

# class FinancieraInteresCuenta(http.Controller):
#     @http.route('/financiera_interes_cuenta/financiera_interes_cuenta/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/financiera_interes_cuenta/financiera_interes_cuenta/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('financiera_interes_cuenta.listing', {
#             'root': '/financiera_interes_cuenta/financiera_interes_cuenta',
#             'objects': http.request.env['financiera_interes_cuenta.financiera_interes_cuenta'].search([]),
#         })

#     @http.route('/financiera_interes_cuenta/financiera_interes_cuenta/objects/<model("financiera_interes_cuenta.financiera_interes_cuenta"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('financiera_interes_cuenta.object', {
#             'object': obj
#         })