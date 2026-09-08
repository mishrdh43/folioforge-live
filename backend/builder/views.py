from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from weasyprint import HTML
import time
import razorpay

RAZORPAY_KEY = "rzp_test_mockkey"
RAZORPAY_SECRET = "rzp_test_mocksecret"
from rest_framework.response import Response
from rest_framework import status
import time
import os
import json
from dotenv import load_dotenv
import pypdf

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)  # Only load .env locally; Railway injects vars directly

class ParseResumeView(APIView):
    def post(self, request):
        text_content = ""
        
        # 1. Check if a file was uploaded (Multipart Form Data)
        if 'resume' in request.FILES:
            pdf_file = request.FILES['resume']
            try:
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            except Exception as e:
                return Response({"error": "Failed to parse PDF file."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 2. Check if raw text was sent via JSON
            text_content = request.data.get('content', '')
            
        if not text_content.strip():
            return Response({"error": "No resume text or file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Use LLM to extract JSON
        prompt = (
            "You are an expert resume parser. Extract the following information from the provided text and strictly output ONLY a valid JSON object matching this exact structure, with no markdown, no code blocks, and nothing outside the JSON:\n"
            "{\n"
            '  "name": "Full Name",\n'
            '  "headline": "A short, professional summary or tag line",\n'
            '  "skills": ["Skill 1", "Skill 2"],\n'
            '  "experience": [\n'
            '    {"role": "Job Title", "company": "Company Name", "dates": "Start - End Date", "desc": "1-2 sentences summarizing responsibilities"}\n'
            "  ],\n"
            '  "projects": [\n'
            '    {"name": "Project Name", "desc": "Short description", "stack": "Tech Stack"}\n'
            "  ]\n"
            "}\n\n"
            f"Resume Text:\n{text_content}"
        )

        try:
            if os.getenv("GEMINI_API_KEY"):
                import requests
                api_key = os.getenv("GEMINI_API_KEY")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1}
                }
                resp = requests.post(url, json=data)
                if resp.status_code != 200:
                    raise Exception(f"Gemini API returned {resp.status_code}: {resp.text}")
                resp_json = resp.json()
                raw_json = resp_json['candidates'][0]['content']['parts'][0]['text']
                
            elif os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                raw_json = completion.choices[0].message.content
                
            else:
                return Response({"error": "No LLM API Key configured in backend/.env"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Clean markdown if LLM returns it
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3]
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3]
                
            parsed_data = json.loads(raw_json.strip())
            return Response(parsed_data, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            return Response({"error": "LLM did not return valid JSON.", "raw": raw_json}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": f"LLM error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GeneratePDFView(APIView):
    def post(self, request):
        profile = request.data.get('profile', {})
        
        # Simple HTML template for the PDF
        html_string = f"""
        <html>
        <head>
            <style>
                @page {{ margin: 2cm; }}
                body {{ font-family: -apple-system, sans-serif; color: #111; line-height: 1.6; }}
                h1 {{ font-size: 28px; margin: 0 0 4px; }}
                .headline {{ font-size: 13px; color: #555; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #333; }}
                h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin: 24px 0 12px; }}
                .skills {{ font-size: 13px; color: #333; margin-bottom: 24px; }}
                .exp-item {{ margin-bottom: 12px; }}
                .exp-header {{ display: flex; justify-content: space-between; font-size: 13.5px; font-weight: bold; }}
                .exp-dates {{ font-weight: normal; color: #555; }}
                .exp-company {{ font-size: 13px; color: #444; font-style: italic; margin-top: 4px; }}
            </style>
        </head>
        <body>
            <h1>{profile.get('name', 'Name')}</h1>
            <div class="headline">{profile.get('headline', '')}</div>
            
            <h2>Skills</h2>
            <div class="skills">{ ' • '.join(profile.get('skills', [])) }</div>
            
            <h2>Experience</h2>
            {"".join([f'<div class="exp-item"><div class="exp-header"><span>{ex.get("role", "")}</span><span class="exp-dates">{ex.get("dates", "")}</span></div><div class="exp-company">{ex.get("company", "")}</div><div class="exp-desc" style="font-size: 13px; color: #333; margin-top: 4px;">{ex.get("desc", "")}</div></div>' for ex in profile.get('experience', [])])}
        </body>
        </html>
        """
        
        # Render PDF using WeasyPrint
        pdf_file = HTML(string=html_string).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="resume.pdf"'
        return response

class CreateOrderView(APIView):
    def post(self, request):
        amount = 2000  # ₹20 in paise
        
        # In production this calls: client.order.create({'amount': amount, 'currency': 'INR', 'payment_capture': '1'})
        # We mock the Razorpay order creation for the prototype:
        mock_order = {
            "id": "order_Mock123456789",
            "entity": "order",
            "amount": amount,
            "currency": "INR",
            "receipt": "receipt#1",
            "status": "created",
        }
        
        return Response(mock_order, status=status.HTTP_200_OK)
