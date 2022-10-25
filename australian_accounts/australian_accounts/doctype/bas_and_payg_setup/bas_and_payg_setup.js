// Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("BAS and PAYG Setup", "onload", function(frm) {
      frm.fields_dict.table_1a.grid.get_field('account').get_query =
			function() {
				return {
					filters: {
						"account_type": "Tax",
						"is_group": "0"
					}
				}
			}
	     frm.fields_dict.table_1b.grid.get_field('account').get_query =
			function() {
				return {
					filters: {
						"account_type": "Tax",
						"is_group": "0"
					}
				}
			}
        frm.fields_dict.table_w1.grid.get_field('account').get_query =
    			function() {
    				return {
    					filters: {
							"root_type": "Expense",
    						"is_group": "0"
    					}
    				}
    			}
})
