# -*- coding: utf-8 -*-
# Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from australian_accounts.australian_accounts import *
from math import floor


class BusinessActivityStatements(Document):
	def before_save(self):
		self.bas_and_payg_setup = frappe.get_doc("BAS and PAYG Setup", self.company)
		if not (self.bas_and_payg_setup):
			frappe.throw("BAS and PAYG setup must be done first")

		self.total_sales_inc_gst = floor(self.get_total_sales_and_gst(self.company, self.fiscal_year, self.quarter))
		self.gst_received = floor(self.get_total_gst_on_sales(self.company, self.fiscal_year, self.quarter))
		self.gst_spent = floor(self.get_total_gst_on_purchases(self.company, self.fiscal_year, self.quarter))
		self.total_salary_wages_other = floor(self.get_salary_wages_payments_w1(self.company, self.fiscal_year, self.quarter))
		self.amounts_withheld_from_total_salary = floor(self.get_salary_wages_withheld_w2(self.company, self.fiscal_year, self.quarter))
		self.total_payment_or_refund = self.amounts_withheld_from_total_salary + self.gst_received + self.paygi - self.gst_spent

	# Get Sales Invoice total including GST
	def get_total_sales_and_gst(self, company, fiscalyear, quarter):
		convertedquarter = convert_quarter(quarter)
		start_date = get_payg_fy_start(fiscalyear)
		end_date = get_payg_fy_end(fiscalyear)
		total = frappe.db.sql("""select 
			sum(si.base_grand_total)
			from `tabSales Invoice` as si
			where docstatus = 1
			AND si.posting_date >= %(start_date)s
			AND si.posting_date <= %(end_date)s
			AND QUARTER(si.posting_date) = %(quarter)s
			AND si.company = %(company)s""", {"company": company, "start_date": start_date, "end_date": end_date, "quarter": convertedquarter})
		
		return flt(total[0][0] if total else 0)

	# Get GST collected on all specified Sales Tax accounts in BAS Setup
	def get_total_gst_on_sales(self, company, fiscalyear, quarter):
		total = 0
		for row in self.bas_and_payg_setup.table_1a:
			total += self.account_gst_on_sales(company, fiscalyear, quarter, row.account)
		return total

	# Get GST collected on specific Sales Tax account specified
	def account_gst_on_sales(self, company, fiscalyear, quarter, account):
		convertedquarter = convert_quarter(quarter)
		total = frappe.db.sql("""SELECT
				SUM(gle.credit - gle.debit) AS expr1
				FROM `tabGL Entry` gle
					LEFT OUTER JOIN `tabJournal Entry` je
						ON gle.voucher_no = je.name
				WHERE gle.company = %(company)s
				AND gle.fiscal_year = %(fiscalyear)s
				AND QUARTER(gle.posting_date) = %(quarter)s
				AND gle.is_cancelled = 0
				AND gle.account = %(account)s
				AND (je.is_bas_entry is NULL
				OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})

		return flt(total[0][0] if total else 0)


	# Get GST paid on all specified Purchase Tax accounts in BAS setup 
	def get_total_gst_on_purchases(self, company, fiscalyear, quarter):
		total = 0
		for row in self.bas_and_payg_setup.table_1b:
			total += self.account_gst_on_purchases(company, fiscalyear, quarter, row.account)
		return total
	
	
	# Get GST figues on specific Purchase Tax account specified
	def account_gst_on_purchases(self, company, fiscalyear, quarter, account):
		convertedquarter = convert_quarter(quarter)
		total = frappe.db.sql("""SELECT
				sum(gle.debit - gle.credit)
				FROM `tabGL Entry` gle
				INNER JOIN tabAccount acc
					ON gle.account = acc.name
				LEFT OUTER JOIN `tabJournal Entry` je
					ON gle.voucher_no = je.name
				WHERE acc.root_type = 'Liability'
				AND acc.is_group = 0
				AND gle.fiscal_year = %(fiscalyear)s
				AND gle.company = %(company)s
				AND QUARTER(gle.posting_date) = %(quarter)s
				AND gle.account = %(account)s
				AND gle.is_cancelled = 0
				AND acc.account_type = 'tax'
				AND (je.is_bas_entry is NULL
				OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})
		return flt(total[0][0] if total else 0)

	# Get Salary gross payments made in specified quarter
	def get_salary_wages_payments_w1(self, company, fiscalyear, quarter):
		convertedquarter = convert_quarter(quarter)
		start_date = get_payg_fy_start(fiscalyear)
		end_date = get_payg_fy_end(fiscalyear)
		total = frappe.db.sql("""select 
			sum(gross_pay)
			from `tabSalary Slip`
			where posting_date >= %(start_date)s
			AND posting_date <= %(end_date)s
			AND company = %(company)s
			AND QUARTER(posting_date) = %(quarter)s
			AND docstatus = 1""", {"company": company, "start_date": start_date, "end_date": end_date, "quarter": convertedquarter})
		return flt(total[0][0] if total else 0)
	
	
	# Get total Salary deductions from accounts specified in BAS Setup 
	def get_salary_wages_withheld_w2(self, company, fiscalyear, quarter):
		total = 0
		for row in self.bas_and_payg_setup.table_w2:
			wf = account_salary_wages_withheld_w2(company, fiscalyear, quarter, row.account)
			if wf > 0:
				total += wf

		if total is None:
			return 0
		else:
			return total	
	
	# Get total Salary deductions from specified account
	def account_salary_wages_withheld_w2(self, company, fiscalyear, quarter, account):
		convertedquarter = convert_quarter(quarter)
		total = frappe.db.sql("""SELECT
				sum(gle.credit)
				FROM `tabGL Entry` gle
				INNER JOIN tabAccount acc
					ON gle.account = acc.name
				LEFT OUTER JOIN `tabJournal Entry` je
					ON gle.voucher_no = je.name
				WHERE acc.root_type = 'Liability'
				AND acc.is_group = 0
				AND gle.fiscal_year = %(fiscalyear)s
				AND gle.company = %(company)s
				AND QUARTER(gle.posting_date) = %(quarter)s
				AND gle.is_cancelled = 0
				AND gle.account = %(account)s
				AND (je.is_bas_entry is NULL
				OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})
		return flt(total[0][0] if total else 0)

	# Function called by button on form
	@frappe.whitelist()
	def make_bas_payment_entry(self):
		self.bas_and_payg_setup = frappe.get_doc("BAS and PAYG Setup", self.company)

		if not(self.bas_and_payg_setup.ato_supplier_account):
			frappe.throw("ATO Supplier must be set up")
		if not (self.bas_and_payg_setup.temp_liab_acc):
			frappe.throw(_("Temp Liability account must be set up"))

		compdefault = frappe.db.get_value('Company', filters={'name': self.company}, fieldname=['default_bank_account','round_off_account','cost_center'])
		postingdate = first_day_of_next_quarter(self.fiscal_year, self.quarter)
	
		# Get linked Journal Entry posted end of quarter
		je = frappe.db.get_value('Journal Entry', filters={'bill_no': self.name, 'posting_date': postingdate.date()}, fieldname='name')
		jejrn = frappe.db.get_value('Journal Entry Account', filters={'parent': je, 'party': self.bas_and_payg_setup.ato_supplier_account}, fieldname=['credit_in_account_currency'])
		
		jedoc = frappe.new_doc("Journal Entry")
		jedoc.posting_date = date.today()
		jedoc.title = 'BAS Payment to ATO '+str(self.quarter)+' '+str(self.fiscal_year)
		jedoc.remark = 'BAS payment Journal Entry to ATO for period '+str(self.quarter)+' '+str(self.fiscal_year)
		jedoc.bill_no = self.name
		jedoc.is_bas_entry = 'Yes'
		jedoc.write_off_based_on = 'Accounts Payable'
	
		jedoc.append("accounts",{
				"account": self.bas_and_payg_setup.temp_liab_acc,
				"party_type": 'Supplier',
				"party": self.bas_and_payg_setup.ato_supplier_account,
				"reference_type": 'Journal Entry',
				"reference_name": je,
				"debit_in_account_currency": jejrn,
				"cost_center": ''
			})
		jedoc.append("accounts",{
				"account": compdefault[0],
				"credit_in_account_currency": math.floor(jejrn),
				"cost_center": ''
			})
		
		# Determine if rouding required and add
		rounding = jejrn - math.floor(jejrn)
		if rounding > 0:
			jedoc.append("accounts",{
				"account": compdefault[1],
				"credit_in_account_currency": rounding,
				"cost_center": compdefault[2]
			})
	
		jedoc.save()
		return jedoc.name
	
	
	# Function called by button on form
	@frappe.whitelist()
	def make_bas_journal_entry(self):
		self.bas_and_payg_setup = frappe.get_doc("BAS and PAYG Setup", self.company)
		if not(self.bas_and_payg_setup.ato_supplier_account):
			frappe.throw("ATO Supplier must be set up")
		if not (self.bas_and_payg_setup.temp_liab_acc):
			frappe.throw(_("Temp Liability account must be set up"))

		roundoff = frappe.db.get_value('Company', filters={'name': self.company}, fieldname=['round_off_account'])
		
		jedoc = frappe.new_doc("Journal Entry")
		jedoc.posting_date = first_day_of_next_quarter(self.fiscal_year, self.quarter)
		jedoc.title = 'BAS Clearing Journal '+str(self.quarter)+' '+str(self.fiscal_year)
		jedoc.remark = 'BAS clearing Journal Entry to Temporary BAS Account for period '+str(self.quarter)+' '+str(self.fiscal_year)
		jedoc.bill_no = self.name
		jedoc.is_bas_entry = 'Yes'
		jedoc.write_off_based_on = 'Accounts Payable'
		totdeb = 0
		totcre = 0
	
		# Add difference amount to Temporary BAS Liability account
		if self.total_payment_or_refund > 0:
			# Payment expected, add in as credit


			jedoc.append("accounts",{
					"account": self.bas_and_payg_setup.temp_liab_acc,
					"party_type": 'Supplier',
					"party": self.bas_and_payg_setup.ato_supplier_account,
					"credit_in_account_currency": self.total_payment_or_refund,
					"cost_center": ''
				})
		elif self.total_payment_or_refund < 0:
			# Refund expected, add in as debit
			jedoc.append("accounts",{
					"account": self.bas_and_payg_setup.temp_liab_acc,
					"party_type": 'Supplier',
					"party": self.bas_and_payg_setup.ato_supplier_account,
					"debit_in_account_currency": self.total_payment_or_refund,
					"cost_center": ''
				})
		
		# Get figures for each Sales GST accounts specified in BAS Setup - add debit figures
		for row in self.bas_and_payg_setup.table_1a:
			db = self.account_gst_on_sales(self.company, self.fiscal_year, self.quarter, row.account)
			if db > 0:
				totdeb += db
				jedoc.append("accounts",{
					"account": row.account,
					"debit_in_account_currency": db,
					"cost_center": ''
				})
		
		# Get figures for each Purchase GST accounts specified in BAS Setup - add credit figures
		for row in self.bas_and_payg_setup.table_1b:
			cd = self.account_gst_on_purchases(self.company, self.fiscal_year, self.quarter, row.account)
			if cd > 0:
				totcre += cd
				jedoc.append("accounts",{
					"account": row.account,
					"credit_in_account_currency": cd,
					"cost_center": ''
				})
	
		# Get Wages held - add debit figures
		for row in self.bas_and_payg_setup.table_w2:
			wf = self.account_salary_wages_withheld_w2(self.company, self.fiscal_year, self.quarter, row.account)
			if wf > 0:
				totdeb += wf
				jedoc.append("accounts",{
					"account": row.account,
					"debit_in_account_currency": wf,
				})
		
		# Round off if difference in amount being sent to ATO
		roundtot = abs(totdeb-totcre) - self.total_payment_or_refund
		if roundtot != 0:
			if roundtot > 0:
				# Add to credit
				jedoc.append("accounts",{
					"account": roundoff,
					"credit_in_account_currency": abs(roundtot),
				})
			elif roundtot < 0:
				# Add to debit
				jedoc.append("accounts",{
					"account": roundoff,
					"debit_in_account_currency": abs(roundtot),
				})
		jedoc.save()
		return jedoc.name
