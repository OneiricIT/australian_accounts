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
		self.bas_and_payg_setup = frappe.get_doc("BAS and PAYG Setup", self.company)
		if not (self.bas_and_payg_setup):
			frappe.throw("BAS and PAYG setup must be done first")

		self.period_start_date = self.get_payg_employee_period_start(self.fiscal_year, self.company, self.employee)
		self.period_end_date = self.get_payg_employee_period_end(self.fiscal_year, self.company, self.employee)
		self.gross_payments = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Grosspayment')
		self.total_tax_withheld = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Tax')
		self.superannuation_payments = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Superannuation - Additional Contribution')
		self.cdep_payments = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'CDEP')
		self.total_allowances = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Allowance')
		self.fb_payments = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Fringe Benefit')
		self.lumpsum_a_payment = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: A')
		self.lumpsum_d_payment = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: D')
		self.lumpsum_e_payment = self.get_payg_employee_payments(self.fiscal_year, self.company, self.employee, 'Lump Sum: E')

		self.fbt_exemption = self.bas_and_payg_setup.fbt_exemption
			
		if len(self.allowances_detail) > 0:
			for row in self.allowances_detail:
				self.get("allowances_detail").remove(row)

		allowance = self.get_payg_allowances_detail(self.fiscal_year, self.company, self.employee)	
		if len(allowance) > 0:
			for row in allowance:
				self.append("allowances_detail",{
					"component": row[0],
					"amount": row[1]
					})


	def get_payg_employee_payments(self, fiscalyear, company, employee, paymenttype):
	
		fystart = 	get_payg_fy_start(fiscalyear)
		fyend = 	get_payg_fy_end(fiscalyear)
		total = 0
		if paymenttype == 'Fringe Benefit':
			now = datetime.now()
			start = str(now.year-1)+'-04-01' #2017-04-01 is start of Fringe Benefit year
			end = str(now.year)+'-03-31' #2018-03-31 is end of Fringe Benefit year
			fbstart = datetime.strptime(str(start), '%Y-%m-%d')
			fbend = datetime.strptime(str(end), '%Y-%m-%d')
	
			total = frappe.db.sql("""SELECT
				SUM(sd.amount)
				FROM `tabSalary Slip` ss
				INNER JOIN `tabSalary Detail` sd
					ON ss.name = sd.parent
				INNER JOIN `tabSalary Component` sc
					ON sd.salary_component = sc.name
				WHERE ss.employee = %(employee)s
				AND sc.payment_type = %(paymenttype)s
				AND (ss.status = 'Submitted'
				OR ss.status = 'Paid')
				AND ss.company = %(company)s
				AND ss.posting_date <= %(fbend)s
				AND ss.posting_date >= %(fbstart)s""", {"company": company, "employee": employee, "fbstart": fbstart, "fbend": fbend, "paymenttype": paymenttype})[0][0]
	
		elif paymenttype =='Grosspayment':
			salcomp = frappe.db.get_all("Salary Component", filters={'disabled': 0, 'do_not_include_in_total': 0, 'type': 'Earning'}, pluck='payment_type')
			for i in salcomp:
				sum = frappe.db.sql("""SELECT
					SUM(sd.amount)
					FROM `tabSalary Slip` ss
					INNER JOIN `tabSalary Detail` sd
						ON ss.name = sd.parent
					INNER JOIN `tabSalary Component` sc
						ON sd.salary_component = sc.name
					WHERE ss.employee = %(employee)s
					#AND `tabSalary Detail`.parentfield = 'earnings'
					AND sc.payment_type = %(paymenttype)s
					AND (ss.status = 'Submitted'
					OR ss.status = 'Paid')
					AND ss.company = %(company)s
					AND ss.posting_date <= %(fyend)s
					AND ss.posting_date >= %(fystart)s""", {"company": company, "employee": employee, "fystart": fystart, "fyend": fyend, "paymenttype": i})[0][0]
				if sum is None:
					pass
				else:
					total += sum
	
		else:
			total = frappe.db.sql("""SELECT
				SUM(sd.amount)
				FROM `tabSalary Slip` ss
				INNER JOIN `tabSalary Detail` sd
					ON ss.name = sd.parent
				INNER JOIN `tabSalary Component` sc
					ON sd.salary_component = sc.name
				WHERE ss.employee = %(employee)s
				#AND `tabSalary Detail`.parentfield = 'earnings'
				AND sc.payment_type = %(paymenttype)s
				AND (ss.status = 'Submitted'
				OR ss.status = 'Paid')
				AND ss.company = %(company)s
				AND ss.posting_date <= %(fyend)s
				AND ss.posting_date >= %(fystart)s""", {"company": company, "employee": employee, "fystart": fystart, "fyend": fyend, "paymenttype": paymenttype})[0][0]
	
		if total is None:
			return 0
		else:
			return math.floor(total)
	
	
	def get_payg_employee_period_start(self, fiscalyear, company, employee):
	
		fystart = get_payg_fy_start(fiscalyear)
		new_fystart = frappe.utils.data.formatdate(fystart)
	
		dbempstart = frappe.db.sql("""SELECT
			`tabEmployee`.date_of_joining
			FROM `tabEmployee`
			WHERE `tabEmployee`.employee = %(employee)s
			AND `tabEmployee`.company = %(company)s""", {"company": company, "employee": employee})[0][0]
	
		empstart = 	frappe.utils.data.formatdate(dbempstart)
	
		if dbempstart > fystart:
			return empstart
		else:
			return new_fystart
	
	
	def get_payg_employee_period_end(self, fiscalyear, company, employee):
	
		fyend = get_payg_fy_end(fiscalyear)
		new_fyend = frappe.utils.data.formatdate(fyend)
	
		dbempend = frappe.db.sql("""SELECT
			`tabEmployee`.relieving_date
			FROM `tabEmployee`
			WHERE `tabEmployee`.employee = %(employee)s
			AND `tabEmployee`.company = %(company)s""", {"company": company, "employee": employee})[0][0]
	
		if dbempend:
			empend = frappe.utils.data.formatdate(dbempend)
			return empend
		else:
			return new_fyend
	
	def get_payg_allowances_detail(self, fiscalyear, company, employee):
	
		fystart = 	get_payg_fy_start(fiscalyear)
		fyend = 	get_payg_fy_end(fiscalyear)
	
		return frappe.db.sql("""SELECT
			sd.salary_component,
			floor(sum(sd.amount))
			FROM `tabSalary Slip` ss
			INNER JOIN `tabSalary Detail` sd
				ON ss.name = sd.parent
			INNER JOIN `tabSalary Component` sc
				ON sd.salary_component = sc.name
			WHERE ss.employee = %(employee)s
			AND sd.parentfield = 'earnings'
			AND sc.payment_type = 'Allowance'
			AND (ss.status = 'Submitted'
			OR ss.status = 'Paid')
			AND ss.company = %(company)s
			AND ss.posting_date <= %(fyend)s
			AND ss.posting_date >= %(fystart)s
			GROUP BY sd.salary_component""", {"company": company, "employee": employee, "fystart": fystart, "fyend": fyend})
		
