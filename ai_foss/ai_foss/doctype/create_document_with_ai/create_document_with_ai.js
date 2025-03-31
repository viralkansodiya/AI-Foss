// Copyright (c) 2025, Viral Patel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Create Document with AI", {
	create(frm) {
        frm.call({
            method : "call_gemini",
            args : {
                prompt : frm.doc.prompt_message,
                pdf_path : frm.doc.document
            },
            callback : (r) =>{
                console.log(r.message)
            }
        })
	},
});
