# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil import relativedelta
from openerp.exceptions import UserError, ValidationError
import time

class FinancieraDescubiertoWizard(models.TransientModel):
	_name = 'financiera.descubierto.wizard'

	descubierto_id = fields.Many2one('financiera.descubierto', string='Descubierto')
	date_invoice = fields.Date('Fecha de la factura', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	journal_id = fields.Many2one('account.journal', string='Diario de Factura')
	use_documents = fields.Boolean('Usa Documento', related='journal_id.use_documents', readonly=True)
	add_date_adicional = fields.Boolean('Calcular interes hasta fecha de la factura')
	# date_adicional = fields.Date('Fecha particular', default=lambda *a: time.strftime('%Y-%m-%d'))

	@api.model
	def default_get(self, fields):
		rec = super(FinancieraDescubiertoWizard, self).default_get(fields)
		context = dict(self._context or {})
		active_id = context.get('active_id')
		rec['date_invoice'] = self.env['account.move.line'].browse(active_id).date
		return rec


	@api.one
	def facturar_descubierto(self):
		context = dict(self._context or {})
		active_ids = context.get('active_ids')
		active_id = context.get('active_id')
		partner_id = self.env['account.move.line'].browse(active_id).partner_id
		interes_adicional = 0
		dias = 0
		if self.add_date_adicional:
			prev_line_id = self.env['account.move.line'].browse(active_ids[0])
			date_start = datetime.strptime(prev_line_id.date, "%Y-%m-%d")
			date_finish = datetime.strptime(self.date_invoice, "%Y-%m-%d")
			dias = date_finish - date_start
			dias = dias.days
			if dias > 0 and prev_line_id.total_balance_receivable > 0:
				interes_adicional = partner_id.rate_per_day * dias * prev_line_id.total_balance_receivable
		fd_values = {
			'partner_id': partner_id.id,
			'date_invoice': self.date_invoice,
			'journal_id': self.journal_id.id,
		}
		descubierto_id = self.env['financiera.descubierto'].create(fd_values)
		descubierto_id.line_ids = active_ids
		amount = 0
		for _id in active_ids:
			line_id = self.env['account.move.line'].browse(_id)
			amount += line_id.interes_no_consolidado_amount
			line_id.interes_computado = True
		amount += interes_adicional
		new_invoice_id = descubierto_id.generate_invoice(self.date_invoice, amount)
		if interes_adicional > 0:
			for line_id in new_invoice_id.move_id.line_ids:
				if line_id.account_id.id == partner_id.property_account_receivable_id.id:
					line_id.interes_computado = True
					line_id.interes_no_consolidado_amount = interes_adicional
					line_id.dias = dias
		descubierto_id.state = 'confirmado'

	@api.multi
	def cancelar_descubierto(self):
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
