# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil import relativedelta
from openerp.exceptions import UserError, ValidationError
import time

class FinancieraDescubiertoWizard(models.TransientModel):
	_name = 'financiera.descubierto.wizard'

	descubierto_id = fields.Many2one('financiera.descubierto', string='Descubierto')
	date_invoice = fields.Date('Fecha', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	journal_id = fields.Many2one('account.journal', string='Diario de Factura')
	use_documents = fields.Boolean('Usa Documento', related='journal_id.use_documents', readonly=True)

	@api.one
	def facturar_descubierto(self):
		context = dict(self._context or {})
		active_ids = context.get('active_ids')
		active_id = context.get('active_id')
		partner_id = self.env['account.move.line'].browse(active_id).partner_id
		fd_values = {
			'partner_id': partner_id.id,
			'date_invoice': self.date_invoice,
			'journal_id': self.journal_id.id,
		}
		new_financiera_descubierto_id = self.env['financiera.descubierto'].create(fd_values)
		descubierto_id = new_financiera_descubierto_id
		descubierto_id.line_ids = active_ids
		amount = 0
		date = None
		for line_id in descubierto_id.line_ids:
			# line_id = self.env['account.move.line'].browse(_id)
			amount += line_id.interes_no_consolidado_amount
			if date == None:
				date = line_id.date
			line_id.interes_computado = True
		descubierto_id.generate_invoice(date, amount)
		descubierto_id.state = 'confirmado'

	@api.multi
	def cancelar_descubierto(self):
		print "CANCELAR DESCUBIERTO"
		context = dict(self._context or {})
		active_ids = context.get('active_ids')
		for _id in active_ids:
			line_id = self.env['account.move.line'].browse(_id)
			if len(line_id.invoice_id) > 0:
				if len(line_id.invoice_id.descubierto_id) > 0:
					for movimiento in line_id.invoice_id.descubierto_id.line_ids:
						movimiento.interes_computado = False
					line_id.invoice_id.descubierto_id.state = 'cancelado'
					if line_id.invoice_id.state == 'open':
						line_id.invoice_id.signal_workflow('invoice_cancel')
