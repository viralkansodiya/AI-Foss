# Copyright (c) 2025, Viral Patel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json


class ConvertToJson(Document):
	def validate(self):
		ai_settings = frappe.get_single("AI Integrations Settings")
		end_point_url = ai_settings.endpoint_url
		api_key = ai_settings.get_password(fieldname="api_key")
		url = f"{end_point_url}?key={api_key}"
		frappe.enqueue(
                    self.call_gemini,
                    queue="default",
                    url=url
                )
		

	def call_gemini(self, url=None):	
		prompt_message= "Provide todays date"
		headers = {'Content-Type': 'application/json'}
		data = {
			"contents": [{
				"parts": [{"text": prompt_message}]
			}]
		}

		
		response = requests.post(url, headers=headers, data=json.dumps(data))
		response.raise_for_status()
		response_json = response.json()
		response_json['candidates'][0]['parts'][0]['text']
		
		