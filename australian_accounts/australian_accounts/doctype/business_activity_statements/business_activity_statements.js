// Copyright (c) 2018, Oneiric Group Pty Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Business Activity Statements", {refresh: function(frm) {
		if(frm.doc.docstatus == 1){
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: 'Journal Entry',
					fieldname: 'name',
					filters: {'bill_no': cur_frm.doc.name}
				},
				callback: function callback(r) {
					if(r.message.length == 0){
						frm.add_custom_button("Make Journal Entry", function() {
							make_bas_journal_entry(frm);
						}).addClass("btn-primary");
					}
					if(r.message.length == 1){
						frm.add_custom_button("Make Payment Entry", function() {
							make_bas_payment_entry(frm);
						}).addClass("btn-primary");
					}
				}
			})
		}
	}
});

let make_bas_journal_entry = function (frm) {
	return frappe.call({
		method: "australian_accounts.australian_accounts.make_bas_journal_entry",
		args: {
			bas_doc: frm.doc.name
		},
		callback: function callback(r) {
			console.log(r.message);
			frappe.set_route(
				'List', 'Journal Entry', {"Journal Entry Account.name": r.message}
			);
		},
		freeze: true,
		freeze_message: __("Creating Journal Entry......")
	});
};

let make_bas_payment_entry = function (frm) {
	return frappe.call({
		method: "australian_accounts.australian_accounts.make_bas_payment_entry",
		args: {
			bas_doc: frm.doc.name
		},
		callback: function callback(r) {
			console.log(r.message);
			frappe.set_route(
				'List', 'Journal Entry', {"Journal Entry Account.name": r.message}
			);
		},
		freeze: true,
		freeze_message: __("Creating Journal Entry......")
	});
};
