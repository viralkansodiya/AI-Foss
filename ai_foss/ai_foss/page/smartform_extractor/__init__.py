import frappe
from frappe.model.document import Document
import requests
import google.generativeai as genai
import base64
import os
import json
from frappe.utils import get_site_path

@frappe.whitelist()
def process_uploaded_files(document_type, employee=None, file_urls=None):

    file_urls = frappe.parse_json(file_urls)
    if(document_type == "Expense Claim"):
        return create_expense_claim(document_type, employee, file_urls)


@frappe.whitelist()
def create_expense_claim(document_type, employee, file_urls):
    prompt_doc = None
    if document_type == "Expense Claim":
        prompt_doc = frappe.db.get_value("Prompt Template", {
                "document_type" : document_type
        }, "name")

    if not prompt_doc:
        frappe.throw("First Create a Prompt Template")



    prompt_template = frappe.get_doc("Prompt Template", prompt_doc)

    prompt = prompt_template.prompt_message


    response_list = []
    try:
        for pdf_path in file_urls:
            if not (prompt):
                frappe.throw("Prompt Message and File is required")

            filename = os.path.basename(pdf_path)
                
            # Determine the full file path (public/private)
            storage_type = "private" if "private" in pdf_path else "public"
            full_path = get_site_path(storage_type, 'files', filename)
            try:
                response_data = call_gemini(prompt, full_path)
                response_data = json.loads(str(response_data))
            except json.JSONDecodeError:
                frappe.throw("Invalid response from Gemini API. Could not parse JSON.")

            response_data["doctype"] = document_type

            if document_type == "Expense Claim":
                if employee := frappe.db.exists("Employee", {"user_id" : frappe.session.user}):
                    response_data["employee"] = employee

            response_list.append(response_data)

        expenses = []
        for row in response_list:
            for ex in row.get("expenses"):
                expenses.append(ex)

        Main_Expense_Claim = response_list[0]
        Main_Expense_Claim["expenses"] = expenses

        new_doc = frappe.get_doc(Main_Expense_Claim)
        new_doc.insert(ignore_permissions=True)

        for row in file_urls:
            file_doc = frappe.new_doc("File")
            file_doc.file_url = row
            file_doc.attached_to_doctype = document_type
            file_doc.attached_to_name = new_doc.name
            file_doc.save()

        return new_doc

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Creation Failed")
        frappe.throw(f"Failed to create Expense Claim: {str(e)}")
    


def call_gemini(prompt, pdf_path):
    ai_settings = frappe.get_single("AI Integrations Settings")
    end_point_url = ai_settings.endpoint_url
    api_key = ai_settings.get_password(fieldname="api_key")
    url = f"{end_point_url}?key={api_key}"
    
    pdf_path = os.path.join("/home/ubuntu/frappe-bench/sites" + pdf_path[1:])

    response = analyze_pdf_with_gemini(api_key, pdf_path, prompt, url)
    response = response.replace('json', '').replace("```", "")
    return response


def pdf_to_base64(pdf_path):
    """Converts a PDF file to a base64 encoded string."""
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode("utf-8")


def analyze_pdf_with_gemini(api_key, pdf_path, prompt, url):

    _, extension = os.path.splitext(pdf_path)

    if extension == ".pdf":
        MIME_TYPE = "application/pdf"
    
    if extension in [".png", ".jpg", ".jpeg"]:
        MIME_TYPE = "image/jpeg"
    
    pdf_base64 = pdf_to_base64(pdf_path)

    headers = {'Content-Type': 'application/json'}

    data = {
			"contents": [
				{
				"parts": [
					{
					"text": prompt
					},
					{
					"inline_data": {
						"mime_type": MIME_TYPE,
						"data": pdf_base64
					}
					}
				]
			}]
		}
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    response_json = response.json()

    return response_json["candidates"][0]["content"]['parts'][0]['text']