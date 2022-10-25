# -*- coding: utf-8 -*-
# Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from australian_accounts.australian_accounts import *
from math import floor

class BusinessActivityStatements(Document):

	def before_save(self):
		if (frappe.db.get_value('BAS and PAYG Setup', filters={'name': self.company})):
			self.total_sales_inc_gst = floor(get_total_sales_and_gst(self.company, self.fiscal_year, self.quarter))
			self.gst_received = floor(get_total_gst_on_sales(self.company, self.fiscal_year, self.quarter))
			self.gst_spent = floor(get_total_gst_on_purchases(self.company, self.fiscal_year, self.quarter))
			self.total_salary_wages_other = floor(get_salary_wages_payments_w1(self.company, self.fiscal_year, self.quarter))
			self.amounts_withheld_from_total_salary = floor(get_salary_wages_withheld_w2(self.company, self.fiscal_year, self.quarter))
			self.total_payment_or_refund = self.amounts_withheld_from_total_salary + self.gst_received + self.paygi - self.gst_spent
		else:
			frappe.throw(msg='BAS Setup has not been completed. Please setup in <a href="/app/bas-and-payg-setup">BAS and PAYG Setup</a>')