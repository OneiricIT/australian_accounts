# -*- coding: utf-8 -*-
# Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import date, datetime
import math
from frappe.utils import now_datetime, formatdate, flt, cint
from frappe.model.naming import make_autoname
from frappe.core.doctype.file.file import get_content_hash
import os
from dateutil.relativedelta import relativedelta


# Get Sales Invoice total including GST
def get_total_sales_and_gst(company, fiscalyear, quarter):

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
		AND si.company = %(company)s""", {"company": company, "start_date": start_date, "end_date": end_date, "quarter": convertedquarter})[0][0]
	if total is None:
		return 0
	else:
		return total


# Get GST collected on all specified Sales Tax accounts in BAS Setup
def get_total_gst_on_sales(company, fiscalyear, quarter):

	bsdoc = frappe.get_doc("BAS and PAYG Setup", company)
	total = 0
	for row in bsdoc.table_1a:
		total += account_gst_on_sales(company, fiscalyear, quarter, row.account)
	return total


# Get GST collected on specific Sales Tax account specified
def account_gst_on_sales(company, fiscalyear, quarter, account):

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
			OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})[0][0]
	if total is None:
		return 0
	else:
		return total


# Get GST paid on all specified Purchase Tax accounts in BAS setup 
def get_total_gst_on_purchases(company, fiscalyear, quarter):

	bsdoc = frappe.get_doc("BAS and PAYG Setup", company)
	total = 0
	for row in bsdoc.table_1b:
		total += account_gst_on_purchases(company, fiscalyear, quarter, row.account)
	return total


# Get GST figues on specific Purchase Tax account specified
def account_gst_on_purchases(company, fiscalyear, quarter, account):

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
			OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})[0][0]
	if total is None:
		return 0
	else:
		return total


# Get Salary gross payments made in specified quarter
def get_salary_wages_payments_w1(company, fiscalyear, quarter):
	
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
		AND docstatus = 1""", {"company": company, "start_date": start_date, "end_date": end_date, "quarter": convertedquarter})[0][0]
	if total is None:
		return 0
	else:
		return total


# Get total Salary deductions from accounts specified in BAS Setup 
def get_salary_wages_withheld_w2(company, fiscalyear, quarter):
	
	bsdoc = frappe.get_doc("BAS and PAYG Setup", company)
	total = 0
	for row in bsdoc.table_w2:
		wf = account_salary_wages_withheld_w2(company, fiscalyear, quarter, row.account)
		if wf > 0:
			total += wf
	if total is None:
		return 0
	else:
		return total


# Get total Salary deductions from specified account
def account_salary_wages_withheld_w2(company, fiscalyear, quarter, account):
	
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
			OR je.is_bas_entry = 'No')""", {"company": company, "fiscalyear": fiscalyear, "quarter": convertedquarter, "account": account})[0][0]
	if total is None:
		return 0
	else:
		return total


# Convert String quarter to DB value
def convert_quarter(quarter):
	quarternum = ''
	if quarter == 'July - September':
		quarternum = '3'
	elif quarter == 'October - December':
		quarternum = '4'
	elif quarter == 'January - March':
		quarternum = '1'
	elif quarter == 'April - June':
		quarternum = '2'
	else:
		frappe.throw("No quarter set")
	return quarternum


# Calculate first date of next specified quarter
def first_day_of_next_quarter(fiscal, quarter):
	q = convert_quarter(quarter)
	if q > '2':
		ydate = datetime.strptime(fiscal[5:], "%Y")
	else:
		ydate = datetime.strptime(fiscal[:4], "%Y")
	mdate = datetime.strptime(quarter.split(' ')[0], "%B")
	if mdate.month is 10:
		mth = 1
	else:
		mth = ((math.floor(((mdate.month - 1) / 3) + 1) - 1) * 3) + 4
	return datetime(year=ydate.year, month=mth, day=1)



@frappe.whitelist()
def get_payg_fy_start(fiscalyear):

	return frappe.db.sql("""SELECT
		`tabFiscal Year`.year_start_date
		FROM `tabFiscal Year`
		WHERE `tabFiscal Year`.name = %(fiscalyear)s""", {"fiscalyear": fiscalyear})[0][0]



@frappe.whitelist()
def get_payg_fy_end(fiscalyear):

	return frappe.db.sql("""SELECT
		`tabFiscal Year`.year_end_date
		FROM `tabFiscal Year`
		WHERE `tabFiscal Year`.name = %(fiscalyear)s""", {"fiscalyear": fiscalyear})[0][0]



def get_payg_fy(postingdate):

	return frappe.db.sql("""SELECT `tabFiscal Year`.year
		FROM `tabFiscal Year`
		WHERE `tabFiscal Year`.year_start_date <= %(postingdate)s
		AND `tabFiscal Year`.year_end_date >= %(postingdate)s
		AND `tabFiscal Year`.disabled = '0'""", {"postingdate": postingdate})[0][0]



@frappe.whitelist()
def get_payg_employee_payments(fiscalyear, company, employee, paymenttype):

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


@frappe.whitelist()
def get_payg_employee_period_start(fiscalyear, company, employee):

	fystart = 	get_payg_fy_start(fiscalyear)
	new_fystart = 	frappe.utils.data.formatdate(fystart)

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



@frappe.whitelist()
def get_payg_employee_period_end(fiscalyear, company, employee):

	fyend = 	get_payg_fy_end(fiscalyear)
	new_fyend = 	frappe.utils.data.formatdate(fyend)

	dbempend = frappe.db.sql("""SELECT
		`tabEmployee`.relieving_date
		FROM `tabEmployee`
		WHERE `tabEmployee`.employee = %(employee)s
		AND `tabEmployee`.company = %(company)s""", {"company": company, "employee": employee})[0][0]

	if dbempend:
		empend = 	frappe.utils.data.formatdate(dbempend)
		return empend
	else:
		return new_fyend


@frappe.whitelist()
def get_payg_allowances_detail(fiscalyear, company, employee):

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
	

@frappe.whitelist()
def make_bas_journal_entry(bas_doc):
	
	bdoc = frappe.get_doc("Business Activity Statements", bas_doc)
	bsdoc = frappe.get_doc("BAS and PAYG Setup", bdoc.company)
	roundoff = frappe.db.get_value('Company', filters={'name': bdoc.company}, fieldname=['round_off_account'])
	
	jedoc = frappe.new_doc("Journal Entry")
	jedoc.posting_date = first_day_of_next_quarter(bdoc.fiscal_year, bdoc.quarter)
	jedoc.title = 'BAS Clearing Journal '+str(bdoc.quarter)+' '+str(bdoc.fiscal_year)
	jedoc.remark = 'BAS clearing Journal Entry to Temporary BAS Account for period '+str(bdoc.quarter)+' '+str(bdoc.fiscal_year)
	jedoc.bill_no = bas_doc
	jedoc.is_bas_entry = 'Yes'
	jedoc.write_off_based_on = 'Accounts Payable'
	totdeb = 0
	totcre = 0

	# Add difference amount to Temporary BAS Liability account
	if bdoc.total_payment_or_refund > 0:
		# Payment expected, add in as credit
		jedoc.append("accounts",{
				"account": bsdoc.temp_liab_acc,
				"party_type": 'Supplier',
				"party": bsdoc.ato_supplier_account,
				"credit_in_account_currency": bdoc.total_payment_or_refund,
				"cost_center": ''
			})
	elif bdoc.total_payment_or_refund < 0:
		# Refund expected, add in as debit
		jedoc.append("accounts",{
				"account": bsdoc.temp_liab_acc,
				"party_type": 'Supplier',
				"party": bsdoc.ato_supplier_account,
				"debit_in_account_currency": bdoc.total_payment_or_refund,
				"cost_center": ''
			})
	
	# Get figures for each Sales GST accounts specified in BAS Setup - add debit figures
	for row in bsdoc.table_1a:
		db = account_gst_on_sales(bdoc.company, bdoc.fiscal_year, bdoc.quarter, row.account)
		if db > 0:
			totdeb += db
			jedoc.append("accounts",{
				"account": row.account,
				"debit_in_account_currency": db,
				"cost_center": ''
			})
	
	# Get figures for each Purchase GST accounts specified in BAS Setup - add credit figures
	for row in bsdoc.table_1b:
		cd = account_gst_on_purchases(bdoc.company, bdoc.fiscal_year, bdoc.quarter, row.account)
		if cd > 0:
			totcre += cd
			jedoc.append("accounts",{
				"account": row.account,
				"credit_in_account_currency": cd,
				"cost_center": ''
			})

	# Get Wages held - add debit figures
	for row in bsdoc.table_w2:
		wf = account_salary_wages_withheld_w2(bdoc.company, bdoc.fiscal_year, bdoc.quarter, row.account)
		if wf > 0:
			totdeb += wf
			jedoc.append("accounts",{
				"account": row.account,
				"debit_in_account_currency": wf,
			})
	
	# Round off if difference in amount being sent to ATO
	roundtot = abs(totdeb-totcre) - bdoc.total_payment_or_refund
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



@frappe.whitelist()
def make_bas_payment_entry(bas_doc):
	bdoc = frappe.get_doc("Business Activity Statements", bas_doc)
	bsdoc = frappe.get_doc("BAS and PAYG Setup", bdoc.company)
	compdefault = frappe.db.get_value('Company', filters={'name': bdoc.company}, fieldname=['default_bank_account','round_off_account','cost_center'])
	postingdate = first_day_of_next_quarter(bdoc.fiscal_year, bdoc.quarter)

	# Get linked Journal Entry posted end of quarter
	je = frappe.db.get_value('Journal Entry', filters={'bill_no': bas_doc, 'posting_date': postingdate.date()}, fieldname='name')
	jejrn = frappe.db.get_value('Journal Entry Account', filters={'parent': je, 'party': bsdoc.ato_supplier_account}, fieldname=['credit_in_account_currency'])
	
	jedoc = frappe.new_doc("Journal Entry")
	jedoc.posting_date = date.today()
	jedoc.title = 'BAS Payment to ATO '+str(bdoc.quarter)+' '+str(bdoc.fiscal_year)
	jedoc.remark = 'BAS payment Journal Entry to ATO for period '+str(bdoc.quarter)+' '+str(bdoc.fiscal_year)
	jedoc.bill_no = bas_doc
	jedoc.is_bas_entry = 'Yes'
	jedoc.write_off_based_on = 'Accounts Payable'

	jedoc.append("accounts",{
			"account": bsdoc.temp_liab_acc,
			"party_type": 'Supplier',
			"party": bsdoc.ato_supplier_account,
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


@frappe.whitelist()
def get_ytd_figures(self, method):
	
	fiscalyear = get_payg_fy(self.posting_date)
	fystart = 	get_payg_fy_start(fiscalyear)
	now = now_datetime().strftime("%Y-%m-%d %H:%M")
	user = frappe.get_user().name
	
	
	for ytd in frappe.db.sql('''SELECT
	sd.salary_component as 'Salary Component',
	sd.abbr as 'Abbreviation',
	replace(format(sum(sd.amount),2), ',', '') as 'Amount'
	FROM `tabSalary Detail` sd
	INNER JOIN `tabSalary Slip` ss
	ON sd.parent = ss.name
	WHERE sd.parentfield = 'earnings'
	AND ss.employee = %(employee)s
	AND (ss.status = 'Submitted' OR ss.status = 'Paid' OR ss.name = %(docname)s)
	AND ss.posting_date <= %(postingdate)s
	AND ss.posting_date >= %(fystart)s
	AND ss.company = %(company)s
	GROUP BY salary_component''', {"company": self.company, "employee": self.employee, "fystart": fystart, "postingdate": self.posting_date, "docname": self.name}):
		frappe.db.sql("""Insert into `tabSalary Slip YTD` (parenttype,creation,modified,modified_by,owner,name,parent,parentfield,salary_component,abbr,amount) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",('Salary Slip',now,now,user,user,make_autoname("SYTDE.########", "Salary Slip YTD"),self.name,'ytd_earning',ytd[0],ytd[1],ytd[2]))
		
	for ytd in frappe.db.sql('''SELECT
	sd.salary_component as 'Salary Component',
	sd.abbr as 'Abbreviation',
	replace(format(sum(sd.amount),2), ',', '') as 'Amount'
	FROM `tabSalary Detail` sd
	INNER JOIN `tabSalary Slip` ss
	ON sd.parent = ss.name
	WHERE sd.parentfield = 'deductions'
	AND ss.employee = %(employee)s
	AND (ss.status = 'Submitted' OR ss.status = 'Paid' OR ss.name = %(docname)s)
	AND ss.posting_date <= %(postingdate)s
	AND ss.posting_date >= %(fystart)s
	AND ss.company = %(company)s
	GROUP BY salary_component''', {"company": self.company, "employee": self.employee, "fystart": fystart, "postingdate": self.posting_date, "docname": self.name}):
		frappe.db.sql("""Insert into `tabSalary Slip YTD` (parenttype,creation,modified,modified_by,owner,name,parent,parentfield,salary_component,abbr,amount) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",('Salary Slip',now,now,user,user,make_autoname("SYTDD.########", "Salary Slip YTD"),self.name,'ytd_deduction',ytd[0],ytd[1],ytd[2]))
	
	total = 0
	for d in self.earnings:
		sc = frappe.db.sql("""Select payment_type from `tabSalary Component` where name=%s""", (d.salary_component))
		for e in sc:
			if e[0] != 'Superannuation' and e[0] != 'Allowance' and e[0] != 'Superannuation - Additional Contribution':
				total += d.amount;
	frappe.db.sql("""Update `tabSalary Slip` set gross_pay_excluding_nontaxable_components=%s where name=%s""",(total, self.name))
	self.reload()


@frappe.whitelist()
def export_stp_to_csv(name,posting_date,is_final_pay_for_this_financial_year,source_type):
    import csv
    float_precision = 2
    with open(frappe.get_site_path('private/files/'+name+'.csv'), 'w') as csvfile:
        fieldnames = ['Entity ABN','Period W1 value','Period W2 value','Payroll number','Period CS deduction Total','Period CS garnishee Total',
                      'Employee TFN','Family name','Given name','Middle name','Date of birth','Hired date','Termination date','Basis of employment code','Termination type',
                      'Address 1','Address 2','Suburb','State/territory','Postcode','Phone','Email','Tax treatment code','Pay period start date','Pay period end date',
                      'Final EOY pay indicator','Income stream code',
                      'Employee gross pay','Employee CDEP','Employee tax','Overtime','Bonus commission','Other leave','Cashout leave','Workers comp leave','Foreign income','Super guarantee amount','RESC',
                      'Kilometer allowance','Transport allowance','Laundry allowance','Meal allowance','Travel allowance',
                      'Other allowance 1 description','Other allowance 1 value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        company=frappe.db.sql("""Select value from `tabSingles` where doctype='Global Defaults' and field='default_company'""")
        if len(company)>0:
            company=[0][0]
        else:
            frappe.throw("Please set the default company in the global defaults.")

        tax_id=frappe.db.sql("""Select tax_id from `tabCompany` where name=%s""",(company))
        if len(tax_id)>=1:
            tax_id=tax_id[0][0]
        else:
            frappe.throw("Tax ID required for company")
        tax_id.replace(" ", "")
        data = []
        fy = get_payg_fy(posting_date)
        fy_start = get_payg_fy_start(fy)
        
        #Need to calculate W1 and W2 figures
        w1_period = 0.00
        w2_period = 0.00
        period_cs_ded = 0.00
        period_cs_gar = 0.00
        
        #if source_type is 'payroll':
        if source_type:
            w1_period= frappe.db.sql("""SELECT round(sum(ss.gross_pay), 2) FROM `tabSalary Slip` ss WHERE ss.payroll_entry = %s AND ss.docstatus = 1""", (name))[0][0]
            w2_period= frappe.db.sql("""SELECT round(sum(ss.total_deduction), 2) FROM `tabSalary Slip` ss WHERE ss.payroll_entry = %s AND ss.docstatus = 1""", (name))[0][0]
            for i in frappe.db.sql("""SELECT ped.employee,pe.start_date,pe.end_date FROM `tabPayroll Employee Detail` ped INNER JOIN `tabPayroll Entry` pe ON ped.parent = pe.name WHERE ped.parent = %s""",(name)):
                overtime=0.00
                bonus=0.00
                other_leave=0.00
                cashout_leave=0.00
                workers_comp=0.00
                kilometer_allowance=0.00
                gross_pay=0.00
                transport_allowance=0.00
                laundry_allowance=0.00
                meal_allowance=0.00
                travel_allowance=0.00
                other_allowance=0.00
                other_allowance_description=0.00
                cdep=0.00
                tax=0.00
                foreign=0.00
                super_guarantee_amount=0.00
                resc=0.00

                for ii in frappe.db.sql("""Select name,gross_pay,total_deduction,start_date,end_date,is_final_pay_for_this_financial_year from `tabSalary Slip` where employee=%s and posting_date>=%s and posting_date<=%s and docstatus=1""",(i[0],fy_start,posting_date)):
                    if not is_final_pay_for_this_financial_year:
                        is_final_pay_for_this_financial_year=ii[5]
                    for earn in frappe.db.sql("""Select amount,salary_component from `tabSalary Detail` where parent=%s and parentfield='earnings'""",(ii[0])):
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where allowance_type='Car' and type='Earning' and name=%s""",(earn[1])))>0:
                           kilometer_allowance+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where allowance_type='Transport' and type='Earning' and name=%s""",(earn[1])))>0:
                            transport_allowance+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where allowance_type='Laundry' and type='Earning' and name=%s """,(earn[1])))>0:
                            laundry_allowance+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where allowance_type='Meal' and type='Earning' and name=%s """,(earn[1])))>0:
                            meal_allowance+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where allowance_type='Travel' and type='Earning' and name=%s""",(earn[1])))>0:
                            travel_allowance+=earn[0]
                        if len(frappe.db.sql("""Select name,description from `tabSalary Component` where allowance_type='Other' and type='Earning' and name=%s""",(earn[1])))>0:
                            other_allowance+=earn[0]
                            other_allowance_description=earn[1]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Bonus' and name=%s""",(earn[1])))>0:
                            bonus+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Overtime' and name=%s""",(earn[1])))>0:
                            overtime+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Personal Leave' and name=%s""",(earn[1])))>0:
                            other_leave+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Annual Leave' and name=%s""",(earn[1])))>0:
                            other_leave+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Leave Cashout' and name=%s""",(earn[1])))>0:
                            cashout_leave+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Workers Compensation' and name=%s""",(earn[1])))>0:
                            workers_comp+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='CDEP' and name=%s""",(earn[1])))>0:
                            cdep+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Foreign' and name=%s""",(earn[1])))>0:
                            foreign+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Superannuation' and name=%s""",(earn[1])))>0:
                            super_guarantee_amount+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Superannuation Additional Contribution' and name=%s""",(earn[1])))>0:
                            resc+=earn[0]
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Salary' and name=%s""",(earn[1])))>0:
                            gross_pay+=earn[0]

                    for dedu in frappe.db.sql("""Select amount,salary_component from `tabSalary Detail` where parent=%s and parentfield='deductions'""",(ii[0])):
                        if len(frappe.db.sql("""Select name from `tabSalary Component` where payment_type='Tax' and name=%s""",(dedu[1])))>0:
                            tax+=dedu[0]

                employee=frappe.db.sql("""Select tax_file_number,last_name,first_name,middle_name,date_of_birth,date_of_joining,relieving_date,employment_basis_code,termination_type_code,address,suburb,state,postcode,cell_number,prefered_email,tax_treatment_code,income_stream_code from `tabEmployee` where name=%s""",(i[0]))
                tfn=""
                family_name=""
                given_name=""
                middle_name=""
                date_of_birth=""
                date_of_joining=""
                termination_date=""
                employment_basis_code=""
                termination_type_code=""
                address1=""
                address2=""
                suburb=""
                state=""
                postcode=""
                phone=""
                email=""
                tax_treatment_code=""
                income_stream_code=""
				
                for e in employee:
                    tfn=e[0]
                    family_name=e[1]
                    given_name=e[2]
                    middle_name=e[3]
                    date_of_birth=e[4]
                    date_of_joining=e[5]
                    termination_date=e[6]
                    employment_basis_code=e[7]
                    termination_type_code=e[8]
                    address1=e[9]
                    suburb=e[10]
                    state=e[11]
                    postcode=e[12]
                    phone=e[13]
                    email=e[14]
                    tax_treatment_code=e[15]
                    income_stream_code=e[16]

                data.append({'Entity ABN': tax_id,
                             'Period W1 value': flt(w1_period, float_precision),
                             'Period W2 value': flt(w2_period, float_precision),'Payroll number': i[0],'Period CS deduction Total': period_cs_ded,'Period CS garnishee Total': period_cs_gar,
                             'Employee TFN': tfn,'Family name': family_name,'Given name': given_name,'Middle name': middle_name,'Date of birth': formatdate(date_of_birth, "d/M/yyyy"),'Hired date': formatdate(date_of_joining, "d/M/yyyy"),'Termination date': formatdate(termination_date, "d/M/yyyy"),
                             'Basis of employment code': employment_basis_code,'Termination type': termination_type_code,'Address 1': address1,'Address 2': address2,'Suburb': suburb,'State/territory': state,'Postcode': postcode,'Phone': phone,'Email': email,
                             'Tax treatment code': tax_treatment_code,'Pay period start date': formatdate(i[1], "d/M/yyyy"),'Pay period end date': formatdate(i[2], "d/M/yyyy"),
                             'Final EOY pay indicator': is_final_pay_for_this_financial_year,'Income stream code': income_stream_code,
                             'Employee gross pay': flt(gross_pay, float_precision),'Employee CDEP': flt(cdep, float_precision),'Employee tax': flt(tax, float_precision),'Overtime': flt(overtime, float_precision),'Bonus commission': flt(bonus, float_precision),'Other leave': flt(other_leave, float_precision),
                             'Cashout leave': flt(cashout_leave, float_precision),'Workers comp leave': flt(workers_comp, float_precision),
                             'Foreign income': flt(foreign, float_precision),'Super guarantee amount': flt(super_guarantee_amount, float_precision),'RESC':flt(resc, float_precision),
                             'Kilometer allowance': flt(kilometer_allowance, float_precision),'Transport allowance': flt(transport_allowance, float_precision),'Laundry allowance': flt(laundry_allowance, float_precision),'Meal allowance': flt(meal_allowance, float_precision),'Travel allowance': flt(travel_allowance, float_precision),
                             'Other allowance 1 description': other_allowance_description,'Other allowance 1 value': flt(other_allowance, float_precision)})
        elif source_type == 'salary':
            return
        else:
            return
        writer.writerows(data)

    file_url = 'private/files/' + name + '.csv'
    content_hash = ''

    with open(frappe.get_site_path(file_url), "rb") as f:
        content_hash = get_content_hash(f.read())

    frappe.db.sql(
        """Insert into `tabFile` (old_parent,folder,name,file_name,is_private,file_size,file_url,attached_to_doctype,attached_to_name,content_hash) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        ('Home/Attachments', 'Home/Attachments', make_autoname("File"),
         name + '.csv', 1,
         os.path.getsize(frappe.get_site_path(file_url)), '/' + file_url, 'Payroll Entry', name,
         content_hash))
    print("writing complete")


@frappe.whitelist()
def new_comment(doctype, docname, comment, email, name):
    return frappe.get_doc({
  'doctype': 'Comment',
  'comment_type': 'Comment',
  'reference_doctype': doctype,
  'reference_name': docname,
  'content': comment,
  'comment_email': email,
  'comment_by': name,
  }).insert()
