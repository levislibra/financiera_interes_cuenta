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
	date = fields.Date('Fecha', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
	date_start = fields.Date('Fecha desde')
	date_finish = fields.Date('Fecha hasta', default=lambda *a: time.strftime('%Y-%m-%d'))
	partner_id = fields.Many2one('res.partner', 'Cliente', required=True)
	account_id = fields.Many2one('account.account', 'Cuenta', related='partner_id.property_account_receivable_id', readonly=True)
	is_credit = fields.Boolean(compute='_compute_is_credit')
	credit = fields.Monetary('Saldo', related='partner_id.credit')
	debit = fields.Monetary('Saldo', related='partner_id.debit')
	currency_id = fields.Many2one('res.currency', string="Moneda", related='account_id.currency_id', readonly=True)
	vat_tax = fields.Boolean('IVA', default=False)
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'sale')]")
	line_ids = fields.One2many('account.move.line', 'descubierto_id', 'Lineas')
	capitalization = fields.Selection([('diaria', 'Diaria'), ('quincenal', 'Quincenal'), ('mensual', 'Mensual')], string='Capitalizacion', required=True, default='mensual')
	rate_per_day = fields.Float('Tasa diaria', digits=(16,6))
	state = fields.Selection([('borrador', 'Borrador'), ('procesando', 'Procesando'),('facturado', 'Facturado'), ('cancelado', 'Cancelado')], string='Estado', readonly=True, default='borrador')
	journal_id = fields.Many2one('account.journal', 'Diario de factura')
	move_ids = fields.One2many('account.move', 'descubierto_id', 'Asientos')
	invoice_ids = fields.One2many('account.invoice', 'descubierto_id', 'Facturas')

	array_lines = [[]]

	@api.model
	def create(self, values):
		print "createeeeeeeeeeeeeeeeeeeeeeeeee"
		rec = super(FinancieraDescubierto, self).create(values)
		config_id = self.env['financiera.descubierto.config'].browse(1)
		rec.update({
			'name': 'Descubierto #' + str(rec.id).zfill(6),
			})
		return rec

	@api.one
	def _compute_is_credit(self):
		self.is_credit = self.partner_id.property_account_receivable_id.user_type_id.type == 'receivable'

	@api.one
	def _compute_matrix(self):
		print "_compute_matrixxxxxxxxxxxxxxxxxxxxx"
		global array_lines
		if self.date_start:
			date_start = datetime.strptime(self.date_start, "%Y-%m-%d")
		if self.date_finish:
			date_finish = datetime.strptime(self.date_finish, "%Y-%m-%d")
		result = date_finish - date_start
		array_lines = [[date_start + timedelta(days=x), None, 0.0] for x in range(0, result.days+1)]
		old_days = -1
		for line_id in self.line_ids:
			current_date = datetime.strptime(line_id.date, "%Y-%m-%d")
			result = current_date - date_start
			print result.days
			if result.days != old_days:
				array_lines[result.days][1] = line_id.total_balance_receivable
			old_days = result.days
		print result.days
		print array_lines

	@api.one
	def _compute_interes(self):
		print "_compute_interessssssssssssssssssss"
		global array_lines
		date_start = datetime.strptime(self.date_start, "%Y-%m-%d")
		date_finish = datetime.strptime(self.date_finish, "%Y-%m-%d")
		i = 0
		len_array_lines = len(array_lines)
		interes_acumulado_mensual = 0
		print array_lines
		while i < len_array_lines:
			line = array_lines[i]
			current_date = line[0]
			print "Current date"
			print current_date			
			# saldo = line[1]+line[2]
			if line[1] == None and i > 0:
				line[1] = array_lines[i-1][1]
				print "asigamos saldo anterior"
			if line[2] > 0:
				# Hay que facturar
				print "Capitalizamos y unificamos saldo"
				line[1] += line[2]
			fin_de_mes = datetime(current_date.year, current_date.month, calendar.monthrange(current_date.year, current_date.month)[1])
			if current_date == fin_de_mes or current_date == date_finish:
				if interes_acumulado_mensual > 0:
					# Hay que facturar::::
					self.generate_invoice(current_date, interes_acumulado_mensual)
					interes_acumulado_mensual = 0
			saldo = line[1]
			print line
			if saldo > 0:
				# Esta debiendo dinero en cuenta
				interes = round(saldo * self.rate_per_day, 2)
				print "interes::"
				print interes
				interes_acumulado_mensual += interes
				if self.capitalization == 'diaria':
					if current_date < date_finish:
						len_array_lines[i+1][2] += interes
				elif self.capitalization == 'quincenal':
					date_biweekly_capitalizacion = datetime(current_date.year, current_date.month, 15)
					date_month_capitalizacion = datetime(current_date.year, current_date.month, calendar.monthrange(current_date.year, current_date.month)[1])
					if current_date.month < 12:
						date_biweekly_next_month_capitalizacion = datetime(current_date.year, current_date.month+1, 15)
					elif current_date.month == 12:
						date_biweekly_next_month_capitalizacion = datetime(current_date.year+1, 1, 15)
					position = 0
					if current_date < date_biweekly_capitalizacion:
						if date_biweekly_capitalizacion <= date_finish:
							print "es quincenal "
							print date_biweekly_capitalizacion
							position = date_biweekly_capitalizacion - date_start
						else:
							print "es date_finish quincenal"
							print date_finish
							position = date_finish - date_start
					elif current_date < date_month_capitalizacion:
						if date_month_capitalizacion <= date_finish:
							print "es date_month_capitalizacion"
							print date_month_capitalizacion
							position = date_month_capitalizacion - date_start
						else:
							print "es date_finish mensual"
							print date_finish
							position = date_finish - date_start
					else:
						# La fecha evaluada es fin de mes
						if date_biweekly_next_month_capitalizacion <= date_finish:
							print "es date_biweekly_next_month_capitalizacion"
							print date_biweekly_next_month_capitalizacion
							position = date_biweekly_next_month_capitalizacion - date_start
						else:
							print "es date_finish next biweekly month"
							print date_finish
							position = date_finish - date_start
					array_lines[position.days][2] += interes
				elif self.capitalization == 'mensual':
					date_month_capitalizacion = datetime(current_date.year, current_date.month, calendar.monthrange(current_date.year, current_date.month)[1])
					if current_date.month < 12:
						date_next_month_capitalizacion = datetime(current_date.year, current_date.month+1, calendar.monthrange(current_date.year, current_date.month)[1])
					elif current_date.month == 12:
						date_next_month_capitalizacion = datetime(current_date.year+1, 1, calendar.monthrange(current_date.year+1, 1)[1])
					print "posibles fechas"
					print date_month_capitalizacion
					print date_next_month_capitalizacion
					print date_finish
					position = 0
					if current_date < date_month_capitalizacion:
						if date_month_capitalizacion <= date_finish:
							print "es date_month_capitalizacion"
							print date_month_capitalizacion
							position = date_month_capitalizacion - date_start
						else:
							print "es date_finish mensual"
							print date_finish
							position = date_finish - date_start
					else:
						# La fecha evaluada es fin de mes
						if date_next_month_capitalizacion <= date_finish:
							print "es date_biweekly_next_month_capitalizacion"
							print date_next_month_capitalizacion
							position = date_next_month_capitalizacion - date_start
						else:
							print "es date_finish month"
							print date_finish
							position = date_finish - date_start
					print "position::"
					print position.days
					array_lines[position.days][2] += interes
			i += 1

	@api.one
	def generate_invoice(self, date, amount):
		currency_id = self.env.user.company_id.currency_id.id
		configuracion_id = self.env['financiera.descubierto.config'].browse(1)
		automatic_validate = configuracion_id.automatic_validate
		# Create invoice line
		ail_ids = []
		vat_tax_id = False
		invoice_line_tax_ids = False
		#if self.currency_id.name != "ARS":
		#	raise ValidationError("Por el momento solo se permite plazos fijos en pesos.")
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
			    'account_id': self.account_id.id,
			    'partner_id': self.partner_id.id,
			    'journal_id': self.journal_id.id,
			    'currency_id': currency_id,
			    'company_id': 1,
			    'date': date,
			    #'document_number': self.document_number,
			    'invoice_line_ids': ail_ids,
			}
			new_invoice_id = self.env['account.invoice'].create(ai_values)
			# if automatic_validate:
			# 	if not self.journal_id.use_documents:
			# 		new_invoice_id.signal_workflow('invoice_open')
			self.invoice_ids = [new_invoice_id.id]


	@api.one
	def set_lines(self):
		print "set_linessssssssssssssssssssssssssss"
		self.line_ids = None
		cr = self.env.cr
		uid = self.env.uid
		move_line_obj = self.pool.get('account.move.line')
		if self.partner_id.last_date_compute_interes == False:
			move_line_ids = move_line_obj.search(cr, uid, [
				('partner_id', '=', self.partner_id.id),
				('account_id', '=', self.account_id.id),
				])
		else:
			move_line_ids = move_line_obj.search(cr, uid, [
				('partner_id', '=', self.partner_id.id),
				('account_id', '=', self.account_id.id),
				('date', '>=', self.partner_id.last_date_compute_interes),
				])
		self.line_ids = move_line_ids
		if len(self.line_ids) > 0:
			self.date_start = self.line_ids[len(self.line_ids)-1].date

	@api.one
	def procesar(self):
		print "procesarrrrrrrrrrrrrrrrrrrrrrrrr"
		self.set_lines()
		self._compute_matrix()
		#self._compute_interes()
		self.state = 'procesando'

	@api.one
	def draft(self):
		print "drafttttttttttttttttttttttttttttttttt"
		self.state = 'borrador'

	@api.multi
	def wizard_descubierto_facturar(self):
		configuracion_id = self.env['financiera.descubierto.config'].browse(1)
		default_journal_id = None
		if len(configuracion_id) > 0:
			default_journal_id = configuracion_id.journal_id
		params = {
			'descubierto_id': self.id,
			'journal_id': default_journal_id.id,
		}
		view_id = self.env['financiera.descubierto.wizard']
		new = view_id.create(params)
		return {
			'type': 'ir.actions.act_window',
			'name': 'Facturar descubierto',
			'res_model': 'financiera.descubierto.wizard',
			'view_type': 'form',
			'view_mode': 'form',
			'res_id'    : new.id,
			'view_id': self.env.ref('financiera_interes_cuenta.descubierto_facturar_wizard', False).id,
			'target': 'new',
		}


class FinancieraDescubiertoConfig(models.Model):
	_name = 'financiera.descubierto.config'

	name = fields.Char('Nombre', defualt='Configuracion general', readonly=True, required=True)
	journal_id = fields.Many2one('account.journal', 'Diario de factura')
	automatic_validate = fields.Boolean('Validacion automatica de facturas', default=True)
	vat_tax = fields.Boolean('IVA', default=False)
	vat_tax_id = fields.Many2one('account.tax', 'Tasa de IVA', domain="[('type_tax_use', '=', 'sale')]")
	capitalization = fields.Selection([('diaria', 'Diaria'), ('quincenal', 'Quincenal'), ('mensual', 'Mensual')], string='Capitalizacion', required=True, default='mensual')
	rate_per_day = fields.Float('Tasa del periodo', digits=(16,6))


class ExtendsAccountMoveLine(models.Model):
	_name = 'account.move.line'
	_inherit = 'account.move.line'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')
	interes_computado = fields.Boolean('Descubierto computado', default=False)

class ExtendsAccountMove(models.Model):
	_name = 'account.move'
	_inherit = 'account.move'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')

class ExtendsAccountInvoice(models.Model):
	_name = 'account.invoice'
	_inherit = 'account.invoice'

	descubierto_id = fields.Many2one('financiera.descubierto', 'Calculo de descubierto')

class ExtendsAccountResPartner(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'

	last_date_compute_interes = fields.Date('Ultima fecha de interes computado', default=False)
