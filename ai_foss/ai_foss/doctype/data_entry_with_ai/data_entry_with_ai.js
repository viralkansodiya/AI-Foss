// Copyright (c) 2025, Viral Patel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Data Entry with AI", {
	refresh(frm) {
        if(frm.doc.status == "Pending"){
            frm.add_custom_button(__('Create'), function() {
                frm.call({
                    method : "create_expense_claim",
                    args : {
                        prompt : frm.doc.prompt_message,
                        pdf_path : frm.doc.document_file
                    },
                    callback : (r) =>{
                        console.log(r.message)
                    }
                })
            });
        }
	},
});
