frappe.pages['smartform-extractor'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'SmartForm Extractor',
        single_column: true
    });

    // Initial layout
	$(wrapper).html('<div class="form-page-content container p-3" id="smartform-extractor-content"><h2>SmartForm Extractor</h2></div>');

    // FieldGroup to hold static fields
    const field_group = new frappe.ui.FieldGroup({
        fields: [
            {
                label: 'Document Type',
                fieldname: 'document_type',
                fieldtype: 'Select',
                options: ['Purchase Invoice', 'Expense Claim'],
                reqd: 1
            },
            {
                label: 'Employee',
                fieldname: 'employee',
                fieldtype: 'Link',
                options: "Employee",
                reqd: 1,
                depends_on: "eval:doc.document_type === 'Expense Claim'"
            },
            {
                label: 'Generate',
                fieldname: 'generate',
                fieldtype: 'Button',
            },
            {
				label : "",
                fieldname: 'column_break_document_type',
                fieldtype: 'Column Break'
            },
			{
				label : "",
                fieldname: 'column_break_document_type2',
                fieldtype: 'Column Break'
            },
			{
				label: 'Attachments',
				fieldname: 'attachments',
				fieldtype: 'HTML',
				options: `
					<div class="flex-col gap-2">
						<label class="cursor-pointer bg-primary text-white px-4 py-2 rounded w-max hover:bg-primary-dark">
							Upload Files
							<input type="file" id="multi_file_upload" multiple class="hidden" />
						</label>
					</div>
					<div id="file_list" class="space-y-1"></div>
                    <div id="dynamic_attach_fields" class="space-y-3 mt-4"></div>
				`
			},			
			{
				label : "",
                fieldname: 'column_break_document_type',
                fieldtype: 'Section Break'
            },
        ],
        body: $('#smartform-extractor-content'),
    });
	field_group.make();

    let uploaded_files = [];

    $('#multi_file_upload').on('change', function (e) {
        const files = e.target.files;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];

        const form_data = new FormData();
        form_data.append('file', file);
        form_data.append('is_private', 0); 
    
        // Upload file using native fetch
        fetch('/api/method/upload_file', {
            method: 'POST',
            body: form_data,
            headers: {
                'X-Frappe-CSRF-Token': frappe.csrf_token
            }
        })
        .then(response => response.json())
        .then(r => {
            if (r.message && r.message.file_url) {
                const file_info = r.message;
                uploaded_files.push(file_info);
        
                // Add to visual list (optional — you can remove this if only Attach fields are needed)
                $('#file_list').append(`
                    <div class="flex items-center justify-between bg-gray-100 rounded p-2" data-fid="${file_info.name}">
                        <a href="${file_info.file_url}" target="_blank" class="text-sm text-primary underline">${file_info.file_name}</a>
                        <button class="remove-file text-red-500 hover:text-red-700 text-xs ml-2" data-fid="${file_info.name}">Remove</button>
                    </div>
                `);
            } else {
                frappe.msgprint(__('Failed to upload file.'));
            }
        })
        
    }
    // Reset file input so same files can be reselected
    $('#multi_file_upload').val('');
});

// On Generate button click
field_group.fields_dict.generate.$wrapper.find('button').on('click', function () {
    const values = field_group.get_values();

    if (!values) {
        frappe.msgprint(__('Please fill all required fields.'));
        return;
    }

    // Basic validation for uploaded files
    if (uploaded_files.length === 0) {
        frappe.msgprint(__('Please upload at least one file.'));
        return;
    }

    // Extract file_urls
    const file_urls = uploaded_files.map(file => file.file_url);
    
    // Optional: Show loader
    frappe.dom.freeze('Processing...');

    frappe.call({
        method: 'ai_foss.ai_foss.page.smartform_extractor.process_uploaded_files', 
        args: {
            document_type: values.document_type,
            employee: values.employee || '',
            file_urls: file_urls
        },
        callback: function (r) {
            frappe.dom.unfreeze();
            if (r.message) {
                const doc_link = `/app/${frappe.router.slug(r.message.doctype)}/${r.message.name}`;
                const doc_name = r.message.name
                // Create the HTML to insert
                const html = `
                    <div class="alert alert-success mt-3">
                        Document <strong><a href="${doc_link}" target="_blank" class="ml-2">${doc_name}</a></strong> created successfully.
                        
                        <button class="btn btn-primary btn-sm ml-2 open-document-dialog" 
                                data-doctype="${r.message.doctype}" 
                                data-name="${r.message.name}">
                            View
                        </button>
                    </div>
                `;
                $('#smartform-extractor-content').append(html);
                frappe.msgprint(__('Process completed successfully.'));
                // You can also redirect or update UI here
            } else {
                frappe.msgprint(__('No response from server.'));
            }
        },
        error: function () {
            frappe.dom.unfreeze();
            frappe.msgprint(__('Something went wrong while processing.'));
        }
    });
});

$('#file_list').on('click', '.remove-file', function () {
    const fid = $(this).data('fid');

    frappe.call('frappe.client.delete', {
        doctype: 'File',
        name: fid
    }).then(() => {
        // Remove from the local uploaded_files array
        uploaded_files = uploaded_files.filter(f => f.name !== fid);

        // Re-render the file list
        render_file_list();
    }).catch(() => {
        frappe.msgprint('Failed to delete file from server.');
    });
});

$(document).on('click', '.open-document-dialog', function () {
    const doctype = $(this).data('doctype');
    const name = $(this).data('name');

    // Fetch document data
    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: doctype,
            name: name
        },
        callback: function (r) {
            if (r.message) {
                const doc = r.message;
    
                // Ensure meta is loaded before accessing fields
                frappe.model.with_doctype(doctype, function () {
                    const meta = frappe.get_meta(doctype);
                    if (!meta || !meta.fields) {
                        frappe.msgprint(`Unable to load metadata for ${doctype}`);
                        return;
                    }
    
                    // Filter out layout-only or unwanted fields
                    const fields = meta.fields.filter(df =>
                        !df.hidden &&
                        df.fieldtype !== 'Tab Break'
                    );

                    fields.forEach(df => {
                        if (df.fieldtype === 'Table' && df.options) {
                            const clild_meta = frappe.get_meta(df.options);
                            const clildfields = clild_meta.fields.filter(df =>
                                !df.hidden 
                            );
                            df.fields=clildfields,
                            df.data=doc[df.fieldname]
                        }
                    });

                    console.log(fields)
                    // Create Dialog
                    const dialog = new frappe.ui.Dialog({
                        title: `${doctype} - ${name}`,
                        size: 'large',
                        fields: fields,
                        data : doc,
                        primary_action_label: 'Update',
                        primary_action(values) {
                            frappe.call({
                                method: 'frappe.client.set_value',
                                args: {
                                    doctype: doctype,
                                    name: name,
                                    fieldname: values
                                },
                                callback: function () {
                                    frappe.msgprint(__('Document updated successfully.'));
                                    dialog.hide();
                                }
                            });
                        }
                    });
    
                    dialog.set_values(doc);
                    dialog.show();
                });
            }
        }
    });
    
});
function render_file_list() {
    const container = $('#file_list');
    container.empty();

    uploaded_files.forEach(file_info => {
        container.append(`
            <div class="flex items-center justify-between bg-gray-100 rounded p-2" data-fid="${file_info.name}">
                <a href="${file_info.file_url}" target="_blank" class="text-sm text-primary underline">${file_info.file_name}</a>
                <button class="remove-file text-red-500 hover:text-red-700 text-xs ml-2" data-fid="${file_info.name}">Remove</button>
            </div>
        `);
    });
    }
}