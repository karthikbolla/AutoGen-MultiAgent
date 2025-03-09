import threading
import time
import smtplib
import os
import requests
from email.message import EmailMessage
from flask import jsonify
import re
import json
import config

import requests

def query_gemini_flash(prompt, api_key):
    """
    Query the Gemini 2.0 Flash model via Google's API endpoint.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if "candidates" in result and len(result["candidates"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print("Unexpected response format:", result)
            return ""
    except requests.exceptions.RequestException as e:
        print(f"Error querying Gemini Flash 2.0: {e}")
        return ""
    
class EmailService:
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.emails_in_progress = False

    def extract_name_from_email(self, email):
        match = re.match(r"([^@]+)", email)
        if match:
            raw_name = match.group(1)
            cleaned = re.sub(r'[^a-zA-Z._]', '', raw_name)
            name_with_spaces = cleaned.replace('.', ' ').replace('_', ' ')
            name_with_spaces = re.sub(r'\s+', ' ', name_with_spaces).strip()
            name = name_with_spaces.title()
            
            return name if name else "Valued Patient"
        return "Valued Patient"

    def generate_email_content(self, health_summary, recipient_email):
        """Generate subject and email body based on health summary using AI."""
        try:
            recipient_name = self.extract_name_from_email(recipient_email)
            
            age_match = re.search(r'age (\d+[-–]\d+|\d+)', health_summary.lower())
            age_range = age_match.group(1) if age_match else "your age group"
            
            conditions = []
            health_keywords = ["cancer", "diabetes", "heart disease", "hypertension", "stroke", "obesity"]
            for keyword in health_keywords:
                if keyword in health_summary.lower():
                    conditions.append(keyword)
            
            condition_text = ', '.join(conditions) if conditions else "your health condition"
            
            prompt = f"""
                As a healthcare communication AI, create a personalized, urgent but professional email for a patient with the following health profile:
                "{health_summary}"

                The email is being sent to: {recipient_email} (Patient Name: {recipient_name})

                IMPORTANT: You must return ONLY a valid JSON object with the exact format shown below, with no additional text, formatting, or explanations:

                {{
                    "subject": "A specific subject line mentioning the key health condition found in the summary",
                    "content": "A 3-4 paragraph email that: 1) Addresses the patient by name, 2) References their specific age range and health condition without being alarmist, 3) Explains why they're receiving this based on risk factors, 4) Provides a clear call-to-action emphasizing urgency but maintaining professionalism."
                }}

                FORMATTING REQUIREMENTS:
                - Use double quotes (") for all JSON keys and string values
                - Do not use single quotes (')
                - Do not include any line breaks within the JSON string values
                - Do not add any markdown, HTML, or other formatting inside the content
                - Do not add any explanatory text before or after the JSON object
                - The entire response must be a single, valid JSON object that can be parsed by json.loads()
                - Paragraphs in the content should be separated with \\n\\n (literal backslash characters followed by n)

                CONTENT REQUIREMENTS:
                - DO NOT use placeholders like [Your Name], [Your Position], or [Your Organization]
                - Instead, determine the specific health issue from the summary and use "Dr. Karthik, Chief [Issue Name] Specialist, Health Vision Smart Center" at the end of the email
                - Use "The Health Vision Team at Health Vision Smart Center" as the signature with "Health Vision [Issue Name] Division" as the department (for example, if the issue is cancer, use "Health Vision Cancer Division")
                - Include the specific phone number 9999999999 for appointments
                - Figure out the appropriate medical specialty based on the patient's health summary

                Make the subject line urgent but not frightening. The email content should be factual about health risks without causing panic.
                """

            for _ in range(3):
                ai_response = query_gemini_flash(prompt=prompt,api_key=config.GEMINI_API_KEY)
                print(f"AI response: {ai_response}")
                response = extract_json_alternative(ai_response)
                print(f"Parsed response: {response}")
                if response:
                    return response
                else:
                    time.sleep(10)

            return {
                "subject": f"Important: {condition_text.title()} Risk Assessment for {age_range}",
                "content": f"Dear {recipient_name},\n\nBased on your recent health information indicating you are in the {age_range} age group with indicators related to {condition_text}, our healthcare team has identified you as being in a potential risk category that warrants immediate attention.\n\nResearch shows that individuals with your specific health profile have significantly better outcomes when proactive measures are taken early. The combination of your age range and health indicators suggests you may benefit from our specialized consultation services.\n\nWe strongly recommend scheduling a consultation with our healthcare specialists within the next 14 days. This preventative step could be crucial for your long-term health management. Please use the consultation button below to book your appointment."
            }

        except Exception as e:
            print(f"Error generating email content: {e}")

            return {
                "subject": "Important Health Alert: Consultation Recommended",
                "content": f"Dear {self.extract_name_from_email(recipient_email)},\n\nBased on your health profile, we've identified potential risk factors that may require professional attention. We recommend scheduling a consultation with our healthcare team at your earliest convenience.\n\nEarly intervention is key to maintaining optimal health outcomes, especially for conditions identified in your profile.\n\nPlease use the consultation button below to schedule your appointment."
            }

    def format_html_email(self, name, body):
        """Create a visually appealing, professional HTML email template for healthcare communications."""
        paragraphs = body.split('\n\n')
        formatted_paragraphs = ''.join([f'<p>{p}</p>' for p in paragraphs if p.strip()])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body, html {{ margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .email-wrapper {{ background-color: #f5f5f5; padding: 20px; }}
                .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 3px 10px rgba(0,0,0,0.1); }}
                .email-header {{ background-color: #1e5d8b; padding: 20px; text-align: center; }}
                .email-header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .email-content {{ padding: 30px 25px; }}
                .salutation {{ font-weight: bold; margin-bottom: 15px; }}
                p {{ margin-bottom: 15px; }}
                .cta-container {{ text-align: center; margin: 30px 0; }}
                .cta-button {{ display: inline-block; background-color: #d9534f; color: white; text-decoration: none; padding: 12px 25px; border-radius: 4px; font-weight: bold; text-align: center; }}
                .cta-button:hover {{ background-color: #c9302c; }}
                .email-footer {{ background-color: #f8f8f8; padding: 15px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #eeeeee; }}
                .confidentiality {{ font-size: 11px; color: #999; margin-top: 15px; font-style: italic; }}
                .urgency-indicator {{ background-color: #ffeaea; border-left: 4px solid #d9534f; padding: 10px 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="email-container">
                    <div class="email-header">
                        <h1>Important Health Information</h1>
                    </div>
                    <div class="email-content">
                        {formatted_paragraphs}
                        <div class="urgency-indicator">
                            <p><strong>Priority Notice:</strong> Early consultation can significantly improve health outcomes for individuals with your profile.</p>
                        </div>
                        <div class="cta-container">
                            <a href="https://healthcare-provider.com/schedule" class="cta-button">Schedule Your Consultation</a>
                        </div>
                        <p>If you have any questions, our healthcare team is available at <strong>karthikbolla123@gmail.com</strong> or call us at <strong>(800) 999999999</strong>.</p>
                        <p>Wishing you the best of health,</p>
                        <p><strong>The Healthcare Team</strong></p>
                        <p class="confidentiality">This message contains confidential health information. If you received this in error, please delete immediately and notify the sender.</p>
                    </div>
                    <div class="email-footer">
                        &copy; 2025 HMulti Agent Helathcare Provider. All rights reserved.<br>
                        123 Sarrornagar, Hyderabad, Telangana 500089
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def send_email(self, recipient_email, subject, content):
        """Send an actual email using SMTP."""
        try:
            if not all([self.smtp_server, self.smtp_port, self.smtp_user, self.smtp_password]):
                return {"status": "SMTP not configured", "success": False}

            name = self.extract_name_from_email(recipient_email)
            html_content = self.format_html_email(name, content)

            msg = EmailMessage()
            msg.set_content(content) 
            msg.add_alternative(html_content, subtype="html")
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = recipient_email

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"Email sent to {recipient_email}")
            return {"status": "sent", "email": recipient_email}
        except Exception as e:
            print(f"Failed to send email to {recipient_email}: {e}")
            return {"status": "failed", "email": recipient_email, "error": str(e)}

    def send_bulk_emails(self, emails, health_summary):
        """Send multiple emails using SMTP in real-time."""
        self.emails_in_progress = True
        results = []

        for email in emails:
            try:
                response = self.generate_email_content(health_summary, email)
                if "subject" not in response or "content" not in response:
                    raise Exception("Invalid response format")
                subject = response.get("subject", "Important Health Alert")
                content = response.get("content", "Error generating email content.")

                result = self.send_email(email, subject, content)
                results.append(result)
                time.sleep(8)
            except Exception as e:
                results.append({"email": email, "status": "failed", "error": str(e)})
                print(f"Failed to send email to {email}: {e}")

        self.emails_in_progress = False
        return results

    def send_bulk_emails_async(self, emails, health_summary):
        """Start email sending in a separate thread."""
        if self.emails_in_progress:
            return {"status": "Emails already in progress", "success": False}

        def email_worker():
            self.send_bulk_emails(emails, health_summary)

        email_thread = threading.Thread(target=email_worker)
        email_thread.daemon = True
        email_thread.start()

        return {"status": f"Started sending {len(emails)} emails", "success": True}

    def get_email_status(self):
        """Check if emails are currently being sent."""
        return {"in_progress": self.emails_in_progress}


def extract_json_alternative(response_text):
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rindex('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx + 1]
            return json.loads(json_str)
        return None
    except Exception as e:
        print(f"Error extracting JSON: {str(e)}")
        return None