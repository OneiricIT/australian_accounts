# -*- coding: utf-8 -*-
# Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from australian_accounts.australian_accounts import *
from math import floor

class PAYGPaymentSummaries(Document):

	def before_save(self):
		if (frappe.db.get_value('BAS and PAYG Setup', filters={'name': self.company})):
			self.period_start_date = get_payg_employee_period_start(self.fiscal_year, self.company, self.employee)
			self.period_end_date = get_payg_employee_period_end(self.fiscal_year, self.company, self.employee)
			self.gross_payments = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Grosspayment')
			self.total_tax_withheld = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Tax')
			self.superannuation_payments = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Superannuation - Additional Contribution')
			self.cdep_payments = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'CDEP')
			self.total_allowances = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Allowance')
			self.fb_payments = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Fringe Benefit')
			self.lumpsum_a_payment = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: A')
			self.lumpsum_d_payment = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: D')
			self.lumpsum_e_payment = get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: E')
			if frappe.db.get_value('BAS and PAYG Setup', filters={'name': self.company}, fieldname=['fbt_exemption']) == 1:
				self.fbt_exemption = 1
			else:
				self.fbt_exemption = 0
			
			if len(self.allowances_detail) > 0:
				for row in self.allowances_detail:
					self.get("allowances_detail").remove(row)
			allowance = get_payg_allowances_detail(self.fiscal_year, self.company, self.employee)	
			if len(allowance) > 0:
				for row in allowance:
					self.append("allowances_detail",{
						"component": row[0],
						"amount": row[1]
						})
		else:
			frappe.throw(msg='BAS Setup has not been completed. Please setup in <a href="/app/bas-and-payg-setup">BAS and PAYG Setup</a>')
