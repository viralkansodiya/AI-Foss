# Copyright (c) 2025, Viral Patel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import google.generativeai as genai
import base64
import json

class CreateDocumentwithAI(Document):
	pass


@frappe.whitelist()
def call_gemini(prompt, pdf_path):
	ai_settings = frappe.get_single("AI Integrations Settings")
	end_point_url = ai_settings.endpoint_url
	api_key = ai_settings.get_password(fieldname="api_key")
	url = f"{end_point_url}?key={api_key}"
	pdf_path = "/home/frappe/frappe-bench/sites/v15viral.fosscrm.com/public" + pdf_path

	response = analyze_pdf_with_gemini(api_key, pdf_path, prompt)
	frappe.throw(str(response))
	return response


def pdf_to_base64(pdf_path):
	"""Converts a PDF file to a base64 encoded string."""
	with open(pdf_path, "rb") as pdf_file:
		return base64.b64encode(pdf_file.read()).decode("utf-8")

def analyze_pdf_with_gemini(api_key, pdf_path, prompt):
	"""Analyzes a PDF using Gemini API and returns JSON data."""

	genai.configure(api_key=api_key)
	model = genai.GenerativeModel('gemini-1.5-pro-002')

	pdf_base64 = pdf_to_base64(pdf_path)

	contents = [
		{
			"mime_type": "application/pdf",
			"data": pdf_base64
		},
		prompt
	]

	try:
		response = model.generate_content(contents)
		response.resolve() #important part, this resolves the promise.
		return response.text
	except Exception as e:
		print(f"An error occurred: {e}")
		return None