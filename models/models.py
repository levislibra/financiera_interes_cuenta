# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil import relativedelta
from openerp.exceptions import UserError, ValidationError
import time
import calendar


class FinancieraDescubierto(models.Model):
	_name = 'financiera.descubierto'

	_order = 'id desc'
	name = fields.Char('Nombre')
	date_invoice = fields.Date('Fecha', required=True)
	partner_id = fields.Many2one('res.partner', 'Cliente', required=True)
	vat_tax = fields.Boolean('IVA', default=False)
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'sale')]")
	line_ids = fields.One2many('account.move.line', 'descubierto_id', 'Lineas')
	automatic_validate = fields.Boolean('Validacion automatica de facturas', default=False)
	capitalization = fields.Selection([('diaria', 'Diaria'), ('mensual', 'Mensual'), ('saldo', 'Saldo Previo')], string='Capitalizacion', required=True, default='mensual')
	rate_per_day = fields.Float('Tasa diaria', digits=(16,6))
	journal_id = fields.Many2one('account.journal', 'Diario de factura')
	move_ids = fields.One2many('account.move', 'descubierto_id', 'Asientos')
	invoice_id = fields.Many2one('account.invoice', 'Factura')
	currency_id = fields.Many2one('res.currency', string="Moneda", related='invoice_id.currency_id')
	amount = fields.Monetary('Interes', related='invoice_id.amount_total')
	state = fields.Selection([('borrador', 'Borrador'), ('confirmado', 'Confirmado'), ('cancelado', 'Cancelado')], string='Estado', readonly=True, default='borrador')
	
	@api.model
	def create(self, values):
		rec = super(FinancieraDescubierto, self).create(values)
		config_id = self.env['financiera.descubierto.config'].browse(1)
		capitalization = config_id.capitalization
		rate_per_day = config_id.rate_per_day
		journal_id = rec.journal_id
		if rec.partner_id.capitalization != None:
			capitalization = rec.partner_id.capitalization
		if rec.partner_id.rate_per_day != 0:
			rate_per_day = rec.partner_id.rate_per_day
		rec.update({
			'name': 'Descubierto #' + str(rec.id).zfill(6),
			'automatic_validate': config_id.automatic_validate,
			'vat_tax': config_id.vat_tax,
			'vat_tax_id': config_id.vat_tax_id.id,
			'capitalization': capitalization,
			'rate_per_day': rate_per_day,
		})
		return rec


	# @api.one
	def generate_invoice(self, date, amount):
		currency_id = self.env.user.company_id.currency_id.id
		# configuracion_id = self.env['financiera.descubierto.config'].browse(1)
		# automatic_validate = configuracion_id.automatic_validate
		# Create invoice line
		ail_ids = []
		vat_tax_id = False
		invoice_line_tax_ids = False
		if self.vat_tax:
			vat_tax_id = self.vat_tax_id.id
			invoice_line_tax_ids = [(6, 0, [vat_tax_id])]

		if amount > 0:
			ail = {
				'name': self.name + " - Intereses",
				'quantity':1,
				'price_unit': amount,
				'vat_tax_id': vat_tax_id,
				'invoice_line_tax_ids': invoice_line_tax_ids,
				'report_invoice_line_tax_ids': invoice_line_tax_ids,
				'account_id': self.journal_id.default_debit_account_id.id,
			}
			ail_ids.append((0,0,ail))

		if len(ail_ids) > 0:
			ai_values = {
				'type': 'out_invoice',
				'description_financiera': self.name + " - Intereses",
			    'account_id': self.partner_id.property_account_receivable_id.id,
			    'partner_id': self.partner_id.id,
			    'journal_id': self.journal_id.id,
			    'currency_id': currency_id,
			    'company_id': 1,
			    'date': date,
			    'invoice_line_ids': ail_ids,
			}
			new_invoice_id = self.env['account.invoice'].create(ai_values)
			if self.automatic_validate:
				if not self.journal_id.use_documents:
					new_invoice_id.signal_workflow('invoice_open')
			self.invoice_id = new_invoice_id.id
			self.invoice_id.descubierto_id = self.id
		return new_invoice_id

	@api.one
	def cancelar_descubierto(self):
		for line_id in self.line_ids:
			line_id.interes_computado = False
				
		self.state = 'cancelado'
		if len(self.invoice_id) > 0 and self.invoice_id.state == 'open':
			self.invoice_id.signal_workflow('invoice_cancel')


class FinancieraDescubiertoConfig(models.Model):
	_name = 'financiera.descubierto.config'

	name = fields.Char('Nombre', defualt='Configuracion general', readonly=True, required=True)
	journal_id = fields.Many2one('account.journal', 'Diario de factura')
	automatic_validate = fields.Boolean('Validacion automatica de facturas', default=False)
	vat_tax = fields.Boolean('IVA', default=False)
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'sale')]")
	capitalization = fields.Selection([('diaria', 'Diaria'), ('quincenal', 'Quincenal'), ('mensual', 'Mensual')], string='Capitalizacion', default='mensual')
	rate_per_day = fields.Float('Tasa del periodo', digits=(16,6))


class ExtendsAccountMoveLine(models.Model):
	_name = 'account.move.line'
	_inherit = 'account.move.line'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')
	interes_no_consolidado_amount = fields.Monetary("Intereses")
	interes_no_consolidado_amount_backup = fields.Monetary("Interes no consolidado")
	interes_no_consolidado_acumulado = fields.Monetary("Interes no consolidado acumulado")
	interes_no_consolidado_acumulado_backup = fields.Monetary("Interes no consolidado acumulado")
	interes_computado = fields.Boolean(' ', default=False)
	dias = fields.Integer('Dias')
	balance_anterior = fields.Float('Balance')


class ExtendsAccountMove(models.Model):
	_name = 'account.move'
	_inherit = 'account.move'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')

class ExtendsAccountInvoice(models.Model):
	_name = 'account.invoice'
	_inherit = 'account.invoice'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')

class ExtendsResPartner(models.Model):
	# _name = 'res.partner'
	_inherit = 'res.partner'

	last_date_compute_interes = fields.Date('Ultima fecha de interes computado', default=False)
	move_line_ids = fields.One2many('account.move.line', 'partner_id', 'Movimientos')
	# move_ids = fields.One2many('account.move', '' 'Asientos fin de mes')
	date_first_move = fields.Date('Primer movimiento', compute='_compute_date_first_move')
	date_last_move = fields.Date('Ultimo movimiento')
	compute_fin_mes = fields.Boolean('Movimientos de fin de mes', default=False)
	journal_fin_de_mes = fields.Many2one('account.journal', 'Diario de saldos')
	capitalization = fields.Selection([('diaria', 'Diaria'), ('mensual', 'Mensual'), ('saldo', 'Saldo Previo')], string='Capitalizacion', required=True, default='mensual')
	rate_per_day = fields.Float('Tasa diaria', digits=(16,6))

	@api.one
	def _compute_date_first_move(self):
		if len(self.move_line_ids) > 0:
			self.date_first_move = self.move_line_ids[len(self.move_line_ids)-1].date
		else:
			self.date_first_move = False

	@api.multi
	def ver_ctacte_cliente(self):
		rec = super(ExtendsResPartner, self).ver_ctacte_cliente()
		self.compute_interes_no_consolidado()
		return rec

	def compute_interes_no_consolidado(self):
		cr = self.env.cr
		uid = self.env.uid
		move_line_obj = self.pool.get('account.move.line')
		move_line_ids = move_line_obj.search(cr, uid, [
			('partner_id', '=', self.id),
			('account_id', '=', self.property_account_receivable_id.id),
		])
		prev_line_id = None
		balance = 0
		i = len(move_line_ids)-1
		interes_mes_anterior = 0
		while i >= 0:
			line_id = self.env['account.move.line'].browse(move_line_ids[i])
			if not line_id.interes_computado and prev_line_id != None:
				date_finish = datetime.strptime(line_id.date, "%Y-%m-%d")
				if prev_line_id != None:
					date_start = datetime.strptime(prev_line_id.date, "%Y-%m-%d")
				
				dias = date_finish - date_start
				dias = dias.days
				line_id.dias = dias
				if dias > 0 and prev_line_id.total_balance_receivable > 0:
					interes = line_id.partner_id.rate_per_day * dias * prev_line_id.total_balance_receivable
					line_id.interes_no_consolidado_amount = interes
			# else:
			# 	line_id.interes_no_consolidado_amount = 0
			i -= 1
			prev_line_id = line_id

