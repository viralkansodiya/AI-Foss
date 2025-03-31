# Copyright (c) 2025, Viral Patel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import google.generativeai as genai
import base64
import os
import json
from frappe.utils import get_site_path


class DataEntrywithAI(Document):
    pass

@frappe.whitelist()
def create_expense_claim(prompt, pdf_path):
    if not (prompt or pdf_file):
        frappe.throw("Prompt Message and File is required")

    try:
        filename = os.path.basename(pdf_path)
            
        # Determine the full file path (public/private)
        storage_type = "private" if "private" in pdf_path else "public"
        full_path = get_site_path(storage_type, 'files', filename)
        try:
            response_data = call_gemini(prompt, full_path)
            response_data = json.loads(str(response_data))
        except json.JSONDecodeError:
            frappe.throw("Invalid response from Gemini API. Could not parse JSON.")

        response_data["docType"] = "Expense Claim"

        if employee := frappe.db.exists("Employee", {"user_id" : frappe.session.user}):
            response_data["employee"] = employee
        doc = frappe.get_doc(response_data)
        doc.insert(ignore_permissions=True)
        return doc.name

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
						"mime_type": "application/pdf",
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
