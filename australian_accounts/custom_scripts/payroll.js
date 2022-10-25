frappe.ui.form.on('Payroll Entry', 'refresh', function (frm) {
    if(cur_frm.doc.docstatus==1){
		if(frm.doc.salary_slips_submitted) {
			frm.add_custom_button("Export to STP CSV", function(){
				frappe.call({
					method: "australian_accounts.australian_accounts.export_stp_to_csv",
					args: {
						'name': frm.doc.name,
						'posting_date': frm.doc.posting_date,
						'is_final_pay_for_this_financial_year': frm.doc.is_final_pay_for_this_financial_year,
						'source_type': 'payroll'
					},
					callback: function(r){
						frappe.call({
							"method": "australian_accounts.australian_accounts.new_comment",
							"args": {
								doctype: cur_frm.doctype,
								docname: cur_frm.docname,
								comment: 'STP for Payroll '+frm.doc.name+' exported to CSV successfully',
								email: frappe.session.user,
								name: frappe.session.user_fullname,
							}
						});
						window.location.replace(window.location.origin+"/private/files/"+frm.doc.name+".csv");
						frm.reload_doc();
					}
				})
			})
		}
    }
})