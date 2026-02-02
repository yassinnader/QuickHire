from typing import Dict, Any, Optional
from xhtml2pdf import pisa
import io
import asyncio
import logging
from datetime import datetime
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self):
        self.resume_templates = {
            "modern": self._get_modern_resume_template(),
            "classic": self._get_classic_resume_template(),
            "creative": self._get_creative_resume_template(),
            "minimal": self._get_minimal_resume_template()
        }
        
        self.cover_letter_templates = {
            "professional": self._get_professional_cover_letter_template(),
            "friendly": self._get_friendly_cover_letter_template(),
            "enthusiastic": self._get_enthusiastic_cover_letter_template(),
            "formal": self._get_formal_cover_letter_template()
        }
        
        # Base CSS for all templates
        self.base_css = """
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                font-size: 11pt;
            }
            
            @page {
                size: A4;
                margin: 0.75in;
            }
            
            .page-break {
                page-break-before: always;
            }
            
            .no-break {
                page-break-inside: avoid;
            }
        """
    
    def health_check(self) -> bool:
        """Check if PDF generator is working properly"""
        try:
            # Test basic PDF generation
            test_html = "<html><body><h1>Test</h1></body></html>"
            result = io.BytesIO()
            pisa_status = pisa.pisaDocument(io.StringIO(test_html), dest=result)
            return not pisa_status.err
        except Exception as e:
            logger.error(f"PDF generator health check failed: {str(e)}")
            return False
    
    def _get_modern_resume_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                }
                
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                .header h1 {
                    font-size: 28pt;
                    font-weight: 300;
                    margin-bottom: 10px;
                    letter-spacing: 2px;
                }
                
                .header .contact-info {
                    font-size: 10pt;
                    opacity: 0.9;
                }
                
                .header .contact-info span {
                    margin: 0 15px;
                }
                
                .section {
                    margin-bottom: 25px;
                    padding: 0 20px;
                }
                
                .section-title {
                    font-size: 14pt;
                    font-weight: bold;
                    color: #667eea;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 5px;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .summary {
                    font-style: italic;
                    color: #666;
                    text-align: justify;
                    margin-bottom: 20px;
                }
                
                .experience-item, .education-item {
                    margin-bottom: 20px;
                    padding-left: 20px;
                    border-left: 3px solid #667eea;
                }
                
                .job-title, .degree {
                    font-size: 12pt;
                    font-weight: bold;
                    color: #333;
                }
                
                .company, .institution {
                    font-size: 11pt;
                    color: #667eea;
                    font-weight: 600;
                }
                
                .date-range {
                    font-size: 9pt;
                    color: #888;
                    float: right;
                    font-style: italic;
                }
                
                .description {
                    margin-top: 8px;
                    text-align: justify;
                }
                
                .description ul {
                    margin-left: 20px;
                    margin-top: 5px;
                }
                
                .description li {
                    margin-bottom: 3px;
                }
                
                .skills-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    margin-top: 10px;
                }
                
                .skill-category {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }
                
                .skill-category h4 {
                    color: #667eea;
                    margin-bottom: 8px;
                    font-size: 10pt;
                }
                
                .skill-list {
                    font-size: 9pt;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{full_name}</h1>
                    <div class="contact-info">
                        <span>{email}</span>
                        {phone_display}
                        {address_display}
                        {linkedin_display}
                        {github_display}
                    </div>
                </div>
                
                {summary_section}
                {experience_section}
                {education_section}
                {skills_section}
            </div>
        </body>
        </html>
        """
    
    def _get_classic_resume_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                .header {
                    text-align: center;
                    border-bottom: 3px solid #333;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                
                .header h1 {
                    font-size: 24pt;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 10px;
                }
                
                .contact-info {
                    font-size: 10pt;
                    color: #666;
                }
                
                .section {
                    margin-bottom: 25px;
                }
                
                .section-title {
                    font-size: 12pt;
                    font-weight: bold;
                    color: #333;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #ccc;
                    padding-bottom: 5px;
                }
                
                .two-column {
                    display: table;
                    width: 100%;
                }
                
                .left-column {
                    display: table-cell;
                    width: 70%;
                    vertical-align: top;
                    padding-right: 20px;
                }
                
                .right-column {
                    display: table-cell;
                    width: 30%;
                    vertical-align: top;
                    padding-left: 20px;
                    border-left: 1px solid #eee;
                }
                
                .experience-item, .education-item {
                    margin-bottom: 20px;
                }
                
                .job-title, .degree {
                    font-size: 11pt;
                    font-weight: bold;
                    color: #333;
                }
                
                .company, .institution {
                    font-size: 10pt;
                    color: #666;
                    font-style: italic;
                }
                
                .date-range {
                    font-size: 9pt;
                    color: #888;
                    float: right;
                }
                
                .description {
                    margin-top: 8px;
                    font-size: 10pt;
                    text-align: justify;
                }
                
                .skills-list {
                    font-size: 10pt;
                    line-height: 1.8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{full_name}</h1>
                    <div class="contact-info">
                        {email} | {phone} | {address}
                        {linkedin_display} {github_display}
                    </div>
                </div>
                
                <div class="two-column">
                    <div class="left-column">
                        {summary_section}
                        {experience_section}
                        {education_section}
                    </div>
                    <div class="right-column">
                        {skills_section}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_creative_resume_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                body {
                    background: linear-gradient(45deg, #f0f2f5 0%, #ffffff 100%);
                }
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                
                .sidebar {
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                    color: white;
                    padding: 30px;
                    width: 35%;
                    float: left;
                    min-height: 100vh;
                }
                
                .main-content {
                    width: 65%;
                    float: right;
                    padding: 30px;
                }
                
                .profile-section {
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                .profile-section h1 {
                    font-size: 20pt;
                    font-weight: 300;
                    margin-bottom: 10px;
                    letter-spacing: 1px;
                }
                
                .profile-section .title {
                    font-size: 12pt;
                    opacity: 0.9;
                    margin-bottom: 20px;
                }
                
                .contact-item {
                    margin-bottom: 10px;
                    font-size: 9pt;
                }
                
                .sidebar .section-title {
                    font-size: 11pt;
                    font-weight: bold;
                    margin-bottom: 15px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid rgba(255,255,255,0.3);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .main-content .section-title {
                    font-size: 14pt;
                    font-weight: bold;
                    color: #ff6b6b;
                    margin-bottom: 20px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .skill-item {
                    margin-bottom: 8px;
                    font-size: 9pt;
                }
                
                .experience-item {
                    margin-bottom: 25px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border-left: 4px solid #ff6b6b;
                }
                
                .job-title {
                    font-size: 12pt;
                    font-weight: bold;
                    color: #333;
                }
                
                .company {
                    font-size: 10pt;
                    color: #ff6b6b;
                    font-weight: 600;
                }
                
                .date-range {
                    font-size: 9pt;
                    color: #888;
                    float: right;
                    background: #fff;
                    padding: 2px 8px;
                    border-radius: 12px;
                }
                
                .clearfix::after {
                    content: "";
                    display: table;
                    clear: both;
                }
            </style>
        </head>
        <body>
            <div class="container clearfix">
                <div class="sidebar">
                    <div class="profile-section">
                        <h1>{full_name}</h1>
                        <div class="title">{job_target}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Contact</div>
                        <div class="contact-item">{email}</div>
                        <div class="contact-item">{phone}</div>
                        <div class="contact-item">{address}</div>
                        {linkedin_display}
                        {github_display}
                    </div>
                    
                    {skills_section}
                </div>
                
                <div class="main-content">
                    {summary_section}
                    {experience_section}
                    {education_section}
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_minimal_resume_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                body {
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    font-weight: 300;
                }
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 40px;
                }
                
                .header {
                    margin-bottom: 40px;
                }
                
                .header h1 {
                    font-size: 32pt;
                    font-weight: 100;
                    color: #333;
                    margin-bottom: 5px;
                    letter-spacing: -1px;
                }
                
                .header .subtitle {
                    font-size: 12pt;
                    color: #666;
                    margin-bottom: 20px;
                }
                
                .contact-info {
                    font-size: 9pt;
                    color: #888;
                    line-height: 1.4;
                }
                
                .section {
                    margin-bottom: 35px;
                }
                
                .section-title {
                    font-size: 10pt;
                    font-weight: 600;
                    color: #333;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    margin-bottom: 20px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }
                
                .experience-item, .education-item {
                    margin-bottom: 20px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #f5f5f5;
                }
                
                .experience-item:last-child,
                .education-item:last-child {
                    border-bottom: none;
                }
                
                .job-title, .degree {
                    font-size: 11pt;
                    font-weight: 400;
                    color: #333;
                }
                
                .company, .institution {
                    font-size: 10pt;
                    color: #888;
                    margin-bottom: 5px;
                }
                
                .date-range {
                    font-size: 9pt;
                    color: #bbb;
                    float: right;
                }
                
                .description {
                    font-size: 10pt;
                    color: #666;
                    margin-top: 10px;
                    line-height: 1.6;
                }
                
                .skills-simple {
                    font-size: 10pt;
                    color: #666;
                    line-height: 1.8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{full_name}</h1>
                    <div class="subtitle">{job_target}</div>
                    <div class="contact-info">
                        {email} · {phone} · {address}
                        {linkedin_display} {github_display}
                    </div>
                </div>
                
                {summary_section}
                {experience_section}
                {education_section}
                {skills_section}
            </div>
        </body>
        </html>
        """
    
    def _get_professional_cover_letter_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 40px;
                }
                
                .header {
                    margin-bottom: 30px;
                }
                
                .sender-info {
                    margin-bottom: 20px;
                }
                
                .sender-info h2 {
                    font-size: 16pt;
                    color: #333;
                    margin-bottom: 5px;
                }
                
                .sender-info .contact {
                    font-size: 10pt;
                    color: #666;
                    line-height: 1.4;
                }
                
                .date {
                    font-size: 10pt;
                    color: #666;
                    margin-bottom: 20px;
                }
                
                .recipient-info {
                    font-size: 10pt;
                    color: #666;
                    margin-bottom: 30px;
                }
                
                .salutation {
                    font-size: 11pt;
                    margin-bottom: 20px;
                }
                
                .content {
                    font-size: 11pt;
                    line-height: 1.6;
                    text-align: justify;
                    margin-bottom: 30px;
                }
                
                .content p {
                    margin-bottom: 15px;
                }
                
                .closing {
                    font-size: 11pt;
                    margin-top: 30px;
                }
                
                .signature {
                    margin-top: 40px;
                    font-size: 11pt;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="sender-info">
                        <h2>{full_name}</h2>
                        <div class="contact">
                            {email}<br>
                            {phone}<br>
                            {address}
                        </div>
                    </div>
                    
                    <div class="date">{date}</div>
                    
                    <div class="recipient-info">
                        {hiring_manager_display}
                        {company_name}<br>
                        {position}
                    </div>
                </div>
                
                <div class="salutation">Dear {salutation},</div>
                
                <div class="content">
                    {content}
                </div>
                
                <div class="closing">
                    <p>Sincerely,</p>
                    <div class="signature">
                        <p>{full_name}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_friendly_cover_letter_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                body {
                    background: #f8f9fa;
                }
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 30px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                
                .header {
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                    text-align: center;
                }
                
                .header h2 {
                    font-size: 18pt;
                    margin-bottom: 10px;
                    font-weight: 300;
                }
                
                .header .contact {
                    font-size: 10pt;
                    opacity: 0.9;
                }
                
                .date-company {
                    background: #e8f5e8;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    font-size: 10pt;
                    color: #2e7d32;
                }
                
                .content {
                    font-size: 11pt;
                    line-height: 1.7;
                    color: #333;
                    margin-bottom: 25px;
                }
                
                .content p {
                    margin-bottom: 15px;
                }
                
                .closing {
                    background: #f1f8e9;
                    padding: 20px;
                    border-radius: 5px;
                    border-left: 4px solid #4CAF50;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{full_name}</h2>
                    <div class="contact">
                        {email} | {phone} | {address}
                    </div>
                </div>
                
                <div class="date-company">
                    <strong>{date}</strong><br>
                    {company_name} - {position}
                </div>
                
                <div class="content">
                    <p>Hello {salutation}!</p>
                    {content}
                </div>
                
                <div class="closing">
                    <p>Best regards,<br><strong>{full_name}</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_enthusiastic_cover_letter_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                
                .letter-content {
                    background: white;
                    color: #333;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }
                
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 2px solid #667eea;
                }
                
                .header h2 {
                    font-size: 20pt;
                    color: #667eea;
                    margin-bottom: 10px;
                }
                
                .exciting-opener {
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                    text-align: center;
                    font-size: 12pt;
                    font-weight: bold;
                }
                
                .content {
                    font-size: 11pt;
                    line-height: 1.7;
                    margin-bottom: 25px;
                }
                
                .content p {
                    margin-bottom: 15px;
                }
                
                .highlight {
                    background: #fff3cd;
                    padding: 15px;
                    border-left: 4px solid #ffc107;
                    margin: 15px 0;
                    border-radius: 4px;
                }
                
                .call-to-action {
                    background: #d4edda;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #28a745;
                    margin-top: 25px;
                    text-align: center;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="letter-content">
                    <div class="header">
                        <h2>{full_name}</h2>
                        <div>{email} | {phone}</div>
                    </div>
                    
                    <div class="exciting-opener">
                        🎯 Excited to Apply for {position} at {company_name}!
                    </div>
                    
                    <div class="content">
                        <p>Dear {salutation},</p>
                        {content}
                    </div>
                    
                    <div class="call-to-action">
                        Looking forward to hearing from you soon!<br>
                        <strong>{full_name}</strong>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_formal_cover_letter_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {base_css}
                
                body {
                    font-family: 'Times New Roman', serif;
                }
                
                .container {
                    max-width: 100%;
                    margin: 0 auto;
                    padding: 50px;
                }
                
                .letterhead {
                    text-align: center;
                    border-bottom: 2px solid #333;
                    padding-bottom: 20px;
                    margin-bottom: 40px;
                }
                
                .letterhead h2 {
                    font-size: 18pt;
                    color: #333;
                    margin-bottom: 10px;
                }
                
                .letterhead .contact {
                    font-size: 10pt;
                    color: #666;
                }
                
                .date {
                    text-align: right;
                    font-size: 11pt;
                    margin-bottom: 30px;
                }
                
                .recipient {
                    font-size: 11pt;
                    margin-bottom: 30px;
                    line-height: 1.4;
                }
                
                .subject-line {
                    font-size: 11pt;
                    font-weight: bold;
                    margin-bottom: 20px;
                    text-decoration: underline;
                }
                
                .salutation {
                    font-size: 11pt;
                    margin-bottom: 20px;
                }
                
                .content {
                    font-size: 11pt;
                    line-height: 1.8;
                    text-align: justify;
                    margin-bottom: 30px;
                }
                
                .content p {
                    margin-bottom: 18px;
                    text-indent: 20px;
                }
                
                .formal-closing {
                    font-size: 11pt;
                    margin-top: 40px;
                }
                
                .signature-block {
                    margin-top: 50px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="letterhead">
                    <h2>{full_name}</h2>
                    <div class="contact">
                        {email} • {phone} • {address}
                    </div>
                </div>
                
                <div class="date">{date}</div>
                
                <div class="recipient">
                    {hiring_manager_display}
                    {company_name}<br>
                    Re: Application for {position}
                </div>
                
                <div class="subject-line">
                    Subject: Formal Application for {position} Position
                </div>
                
                <div class="salutation">Dear {salutation}:</div>
                
                <div class="content">
                    {content}
                </div>
                
                <div class="formal-closing">
                    <p>Respectfully yours,</p>
                    <div class="signature-block">
                        <p>{full_name}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    async def generate_pdf_async(self, content: str, template_type: str, style: str = "modern") -> bytes:
        """Generate PDF asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_pdf, content, template_type, style)
    
    def generate_pdf(self, content: Dict[str, Any], template_type: str, style: str = "modern") -> bytes:
        """Generate PDF with enhanced templates and error handling"""
        try:
            if template_type == "resume":
                html = self._generate_resume_html(content, style)
            elif template_type == "cover_letter":
                html = self._generate_cover_letter_html(content, style)
            else:
                raise ValueError(f"Unknown template type: {template_type}")
            
            # Generate PDF
            result = io.BytesIO()
            pisa_status = pisa.pisaDocument(io.StringIO(html), dest=result)
            
            if pisa_status.err:
                logger.error(f"PDF generation failed with errors: {pisa_status.err}")
                raise Exception("PDF generation failed")
            
            result.seek(0)
            return result.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise
    
    def _generate_resume_html(self, content: Dict[str, Any], style: str) -> str:
        """Generate HTML for resume using specified style"""
        template = self.resume_templates.get(style, self.resume_templates["modern"])
        
        # Prepare contact information displays
        phone_display = f"<span>{content.get('phone', '')}</span>" if content.get('phone') else ""
        address_display = f"<span>{content.get('address', '')}</span>" if content.get('address') else ""
        linkedin_display = f"<span>{content.get('linkedin', '')}</span>" if content.get('linkedin') else ""
        github_display = f"<span>{content.get('github', '')}</span>" if content.get('github') else ""
        
        # Generate sections
        summary_section = self._generate_summary_section(content.get('summary', ''))
        experience_section = self._generate_experience_section(content.get('experience', []))
        education_section = self._generate_education_section(content.get('education', []))
        skills_section = self._generate_skills_section(content.get('skills', {}), style)
        
        # Format the template
        html = template.format(
            base_css=self.base_css,
            full_name=content.get('full_name', ''),
            email=content.get('email', ''),
            phone=content.get('phone', ''),
            address=content.get('address', ''),
            phone_display=phone_display,
            address_display=address_display,
            linkedin_display=linkedin_display,
            github_display=github_display,
            job_target=content.get('job_target', ''),
            summary_section=summary_section,
            experience_section=experience_section,
            education_section=education_section,
            skills_section=skills_section
        )
        
        return html
    
    def _generate_cover_letter_html(self, content: Dict[str, Any], style: str) -> str:
        """Generate HTML for cover letter using specified style"""
        template = self.cover_letter_templates.get(style, self.cover_letter_templates["professional"])
        
        # Prepare hiring manager display
        hiring_manager = content.get('hiring_manager', '')
        if hiring_manager:
            hiring_manager_display = f"{hiring_manager}<br>"
        else:
            hiring_manager_display = "Hiring Manager<br>"
        
        # Prepare salutation
        if hiring_manager and hiring_manager != "Hiring Manager":
            salutation = hiring_manager.split()[0] if ' ' in hiring_manager else hiring_manager
        else:
            salutation = "Hiring Manager"
        
        # Format date
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Generate content paragraphs
        content_paragraphs = self._generate_cover_letter_content(content)
        
        # Format the template
        html = template.format(
            base_css=self.base_css,
            full_name=content.get('full_name', ''),
            email=content.get('email', ''),
            phone=content.get('phone', ''),
            address=content.get('address', ''),
            date=current_date,
            hiring_manager_display=hiring_manager_display,
            company_name=content.get('company_name', ''),
            position=content.get('position', ''),
            salutation=salutation,
            content=content_paragraphs
        )
        
        return html
    
    def _generate_summary_section(self, summary: str) -> str:
        """Generate summary section HTML"""
        if not summary:
            return ""
        
        return f"""
        <div class="section no-break">
            <div class="section-title">Professional Summary</div>
            <div class="summary">{summary}</div>
        </div>
        """
    
    def _generate_experience_section(self, experiences: list) -> str:
        """Generate experience section HTML"""
        if not experiences:
            return ""
        
        html = '<div class="section"><div class="section-title">Professional Experience</div>'
        
        for exp in experiences:
            # Format date range
            start_date = exp.get('start_date', '')
            end_date = exp.get('end_date', 'Present')
            date_range = f"{start_date} - {end_date}" if start_date else ""
            
            # Format description
            description = exp.get('description', '')
            if isinstance(description, list):
                desc_html = "<ul>"
                for item in description:
                    desc_html += f"<li>{item}</li>"
                desc_html += "</ul>"
            else:
                desc_html = f"<p>{description}</p>"
            
            html += f"""
            <div class="experience-item no-break">
                <div class="job-title">{exp.get('title', '')}</div>
                <div class="company">{exp.get('company', '')}</div>
                <div class="date-range">{date_range}</div>
                <div style="clear: both;"></div>
                <div class="description">{desc_html}</div>
            </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_education_section(self, education: list) -> str:
        """Generate education section HTML"""
        if not education:
            return ""
        
        html = '<div class="section"><div class="section-title">Education</div>'
        
        for edu in education:
            # Format date range
            start_date = edu.get('start_date', '')
            end_date = edu.get('end_date', '')
            date_range = f"{start_date} - {end_date}" if start_date and end_date else end_date
            
            # Additional details
            gpa = edu.get('gpa', '')
            honors = edu.get('honors', '')
            details = []
            if gpa:
                details.append(f"GPA: {gpa}")
            if honors:
                details.append(honors)
            
            details_html = f"<div class='description'>{', '.join(details)}</div>" if details else ""
            
            html += f"""
            <div class="education-item no-break">
                <div class="degree">{edu.get('degree', '')}</div>
                <div class="institution">{edu.get('institution', '')}</div>
                <div class="date-range">{date_range}</div>
                <div style="clear: both;"></div>
                {details_html}
            </div>
            """
        
        html += '</div>'
        return html
    
    def _generate_skills_section(self, skills: dict, style: str) -> str:
        """Generate skills section HTML based on style"""
        if not skills:
            return ""
        
        html = '<div class="section"><div class="section-title">Skills</div>'
        
        if style == "modern":
            html += '<div class="skills-grid">'
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    skills_text = ", ".join(skill_list)
                else:
                    skills_text = str(skill_list)
                
                html += f"""
                <div class="skill-category">
                    <h4>{category}</h4>
                    <div class="skill-list">{skills_text}</div>
                </div>
                """
            html += '</div>'
            
        elif style == "creative":
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    skills_text = ", ".join(skill_list)
                else:
                    skills_text = str(skill_list)
                
                html += f"""
                <div class="section-title">{category}</div>
                <div class="skill-item">{skills_text}</div>
                """
                
        else:  # classic, minimal
            if style == "minimal":
                html += '<div class="skills-simple">'
            else:
                html += '<div class="skills-list">'
            
            for category, skill_list in skills.items():
                if isinstance(skill_list, list):
                    skills_text = ", ".join(skill_list)
                else:
                    skills_text = str(skill_list)
                
                html += f"<strong>{category}:</strong> {skills_text}<br>"
            
            html += '</div>'
        
        html += '</div>'
        return html
    
    def _generate_cover_letter_content(self, content: Dict[str, Any]) -> str:
        """Generate cover letter content paragraphs"""
        paragraphs = content.get('paragraphs', [])
        
        if not paragraphs:
            # Generate default content if none provided
            company_name = content.get('company_name', '[Company Name]')
            position = content.get('position', '[Position]')
            
            paragraphs = [
                f"I am writing to express my strong interest in the {position} position at {company_name}. With my background and experience, I am confident that I would be a valuable addition to your team.",
                "My professional experience has equipped me with the skills and knowledge necessary to excel in this role. I am particularly drawn to this opportunity because it aligns perfectly with my career goals and allows me to contribute to your organization's continued success.",
                "I would welcome the opportunity to discuss how my qualifications can benefit your team. Thank you for considering my application, and I look forward to hearing from you soon."
            ]
        
        html = ""
        for paragraph in paragraphs:
            html += f"<p>{paragraph}</p>"
        
        return html
    
    def generate_pdf_base64(self, content: Dict[str, Any], template_type: str, style: str = "modern") -> str:
        """Generate PDF and return as base64 string"""
        pdf_bytes = self.generate_pdf(content, template_type, style)
        return base64.b64encode(pdf_bytes).decode('utf-8')
    
    def save_pdf_to_file(self, content: Dict[str, Any], template_type: str, 
                        output_path: str, style: str = "modern") -> bool:
        """Generate PDF and save to file"""
        try:
            pdf_bytes = self.generate_pdf(content, template_type, style)
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info(f"PDF saved successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving PDF to file: {str(e)}")
            return False
    
    def get_available_templates(self) -> Dict[str, list]:
        """Get list of available templates"""
        return {
            "resume": list(self.resume_templates.keys()),
            "cover_letter": list(self.cover_letter_templates.keys())
        }
    
    def validate_content(self, content: Dict[str, Any], template_type: str) -> Dict[str, Any]:
        """Validate and sanitize content for PDF generation"""
        validated = {}
        
        if template_type == "resume":
            # Required fields for resume
            validated['full_name'] = content.get('full_name', '').strip()
            validated['email'] = content.get('email', '').strip()
            validated['phone'] = content.get('phone', '').strip()
            validated['address'] = content.get('address', '').strip()
            
            # Optional fields
            validated['linkedin'] = content.get('linkedin', '').strip()
            validated['github'] = content.get('github', '').strip()
            validated['job_target'] = content.get('job_target', '').strip()
            validated['summary'] = content.get('summary', '').strip()
            
            # Lists
            validated['experience'] = content.get('experience', [])
            validated['education'] = content.get('education', [])
            validated['skills'] = content.get('skills', {})
            
        elif template_type == "cover_letter":
            # Required fields for cover letter
            validated['full_name'] = content.get('full_name', '').strip()
            validated['email'] = content.get('email', '').strip()
            validated['phone'] = content.get('phone', '').strip()
            validated['address'] = content.get('address', '').strip()
            validated['company_name'] = content.get('company_name', '').strip()
            validated['position'] = content.get('position', '').strip()
            
            # Optional fields
            validated['hiring_manager'] = content.get('hiring_manager', '').strip()
            validated['paragraphs'] = content.get('paragraphs', [])
        
        return validated

# Example usage and testing
if __name__ == "__main__":
    # Example resume data
    resume_data = {
        "full_name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "(555) 123-4567",
        "address": "123 Main St, City, State 12345",
        "linkedin": "linkedin.com/in/johndoe",
        "github": "github.com/johndoe",
        "job_target": "Software Developer",
        "summary": "Experienced software developer with 5+ years of experience in full-stack development. Passionate about creating efficient, scalable solutions and working with cutting-edge technologies.",
        "experience": [
            {
                "title": "Senior Software Developer",
                "company": "Tech Corp",
                "start_date": "2020",
                "end_date": "Present",
                "description": [
                    "Led development of microservices architecture serving 1M+ users",
                    "Mentored junior developers and conducted code reviews",
                    "Implemented CI/CD pipelines reducing deployment time by 60%"
                ]
            },
            {
                "title": "Software Developer",
                "company": "StartupXYZ",
                "start_date": "2018",
                "end_date": "2020",
                "description": "Developed full-stack web applications using React, Node.js, and MongoDB. Collaborated with design team to implement responsive UI/UX."
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "institution": "University of Technology",
                "start_date": "2014",
                "end_date": "2018",
                "gpa": "3.8",
                "honors": "Magna Cum Laude"
            }
        ],
        "skills": {
            "Programming Languages": ["JavaScript", "Python", "Java", "TypeScript"],
            "Frameworks": ["React", "Node.js", "Express", "Django"],
            "Databases": ["MongoDB", "PostgreSQL", "Redis"],
            "Tools": ["Git", "Docker", "AWS", "Jenkins"]
        }
    }
    
    # Example cover letter data
    cover_letter_data = {
        "full_name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "(555) 123-4567",
        "address": "123 Main St, City, State 12345",
        "company_name": "Amazing Tech Company",
        "position": "Senior Software Developer",
        "hiring_manager": "Sarah Johnson",
        "paragraphs": [
            "I am excited to apply for the Senior Software Developer position at Amazing Tech Company. With over 5 years of experience in full-stack development and a proven track record of delivering scalable solutions, I am confident I would be a valuable addition to your development team.",
            "In my current role at Tech Corp, I have successfully led the development of microservices architecture that serves over 1 million users daily. I have extensive experience with the technologies mentioned in your job posting, including React, Node.js, and cloud services. My ability to mentor junior developers and collaborate effectively with cross-functional teams aligns perfectly with your team's needs.",
            "I am particularly drawn to Amazing Tech Company's commitment to innovation and your recent expansion into AI-powered solutions. I would welcome the opportunity to discuss how my technical expertise and leadership experience can contribute to your continued success."
        ]
    }
    
    # Test the PDF generator
    try:
        generator = PDFGenerator()
        
        # Health check
        if generator.health_check():
            print("PDF Generator is working correctly!")
            
            # Generate resume PDF
            resume_pdf = generator.generate_pdf(resume_data, "resume", "modern")
            print(f"Resume PDF generated successfully! Size: {len(resume_pdf)} bytes")
            
            # Generate cover letter PDF
            cover_letter_pdf = generator.generate_pdf(cover_letter_data, "cover_letter", "professional")
            print(f"Cover letter PDF generated successfully! Size: {len(cover_letter_pdf)} bytes")
            
            # Show available templates
            templates = generator.get_available_templates()
            print(f"Available templates: {templates}")
            
        else:
            print("PDF Generator health check failed!")
            
    except Exception as e:
        print(f"Error testing PDF generator: {str(e)}")