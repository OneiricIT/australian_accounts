# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "australian_accounts"
app_title = "Australian Accounts"
app_publisher = "Oneiric Group Pty Ltd"
app_description = "Accounts additions and customisations for Australian market"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "support@oneiric.com.au"
app_license = "MIT"


fixtures = [{"dt":"Custom Field", "filters": [["fieldname", 'in', ("payment_type", "tax_file_number", "bank_bsb", "superfund", "supermembernumber", "gross_pay_excluding_nontaxable_components", "payment_type", "gross_payment_type", "column_break_56", "ytd_info", "ytd_deduction", "ytd_earning", "bank_bsb", "super_fund", "super_member", "tax_file_number", "is_bas_entry")]]},
			{"dt":"Workspace", "filters": {"module": "Australian Accounts"}}
       ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/australian_accounts/css/australian_accounts.css"
# app_include_js = "/assets/australian_accounts/js/australian_accounts.js"

# include js, css files in header of web template
# web_include_css = "/assets/australian_accounts/css/australian_accounts.css"
# web_include_js = "/assets/australian_accounts/js/australian_accounts.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

doctype_js = {"Payroll Entry" : "custom_scripts/payroll.js",
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "australian_accounts.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "australian_accounts.install.before_install"
# after_install = "australian_accounts.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "australian_accounts.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

doc_events = {
"Salary Slip": {
		"on_submit": "australian_accounts.australian_accounts.get_ytd_figures"

	},
	}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"australian_accounts.tasks.all"
# 	],
# 	"daily": [
# 		"australian_accounts.tasks.daily"
# 	],
# 	"hourly": [
# 		"australian_accounts.tasks.hourly"
# 	],
# 	"weekly": [
# 		"australian_accounts.tasks.weekly"
# 	]
# 	"monthly": [
# 		"australian_accounts.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "australian_accounts.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "australian_accounts.event.get_events"
# }
