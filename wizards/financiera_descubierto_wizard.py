# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime, timedelta
from dateutil import relativedelta
from openerp.exceptions import UserError, ValidationError
import time

class FinancieraDescubiertoWizard(models.TransientModel):
    _name = 'financiera.descubierto.wizard'

    descubierto_id = fields.Many2one('financiera.descubierto', string='Descubierto')
    journal_id = fields.Many2one('account.journal', string='Diario de Factura')
    use_documents = fields.Boolean('Usa Documento', related='journal_id.use_documents', readonly=True)

    @api.one
    def facturar_descubierto(self):
        descubierto_id = self.descubierto_id
        descubierto_id.journal_id = self.journal_id
        descubierto_id._compute_interes()
        descubierto_id.set_lines()

    @api.one
    def cancelar_descubierto(self):
        descubierto_id = self.descubierto_id
        descubierto_id.cancelar_descubierto()