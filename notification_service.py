import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import copy

class NotificationService:
    """
    🚀 NotificationService: Robust, extensible notification manager for email (and future channels).
    Features:
        - Async, queue-based, and bulk notification system
        - Configurable SMTP (and extensible for other channels)
        - Complete logging, error handling, and queue inspection
        - HTML/plaintext support
        - Modern Python typing and idioms
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.email_config: Dict[str, Union[str, int]] = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': '',
            'password': '',
        }
        self.notifications_queue: List[Dict[str, Any]] = []
        self.logger = logger or self._default_logger()
        self._lock = asyncio.Lock()

    @staticmethod
    def _default_logger() -> logging.Logger:
        logger = logging.getLogger("NotificationService")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def configure_email(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """Configure SMTP email settings dynamically."""
        self.email_config.update({
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
        })
        self.logger.info("Email configuration updated.")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        *,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send an email notification (supports HTML and attachments).
        """
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.email_config['username']
            msg['To'] = to_email

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Attach files if provided
            if attachments:
                from email.mime.base import MIMEBase
                from email import encoders
                for att in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(att['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{att["filename"]}"'
                    )
                    msg.attach(part)

            # Async-friendly SMTP send
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email_sync, msg, to_email)
            self.logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_email_sync(self, msg: MIMEMultipart, to_email: str):
        """Synchronous SMTP send, called in executor to not block event loop."""
        with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
            server.ehlo()
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.sendmail(
                self.email_config['username'],
                to_email,
                msg.as_string()
            )

    # --- Notification Templates ---

    @staticmethod
    def _template_job_application(job_title: str, applicant_name: str) -> str:
        return (
            f"Dear Employer,\n\n"
            f"You have received a new application for the position: {job_title}\n\n"
            f"Applicant: {applicant_name}\n"
            f"Application Date: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "Please log in to your QuickHire dashboard to review the application.\n\n"
            "Best regards,\nQuickHire Team"
        )

    @staticmethod
    def _template_application_confirmation(job_title: str, company_name: str) -> str:
        return (
            f"Dear Applicant,\n\n"
            f"Thank you for applying to the position: {job_title} at {company_name}\n\n"
            "Your application has been successfully submitted and is now under review.\n\n"
            f"Application Date: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "You will be notified of any updates regarding your application status.\n\n"
            "Best regards,\nQuickHire Team"
        )

    @staticmethod
    def _template_status_update(job_title: str, status: str, message: str = "") -> str:
        return (
            f"Dear Applicant,\n\n"
            f"Your application status for {job_title} has been updated.\n\n"
            f"New Status: {status}\n\n"
            f"{message}\n\n"
            f"Date: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "Best regards,\nQuickHire Team"
        )

    # --- Notification Senders ---

    async def send_job_application_notification(self, employer_email: str, job_title: str, applicant_name: str) -> bool:
        """Send notification to employer about new job application."""
        subject = f"New Application for {job_title}"
        body = self._template_job_application(job_title, applicant_name)
        return await self.send_email(employer_email, subject, body)

    async def send_application_confirmation(self, applicant_email: str, job_title: str, company_name: str) -> bool:
        """Send confirmation to applicant."""
        subject = f"Application Confirmation - {job_title}"
        body = self._template_application_confirmation(job_title, company_name)
        return await self.send_email(applicant_email, subject, body)

    async def send_status_update(self, applicant_email: str, job_title: str, status: str, message: str = "") -> bool:
        """Send application status update."""
        subject = f"Application Status Update - {job_title}"
        body = self._template_status_update(job_title, status, message)
        return await self.send_email(applicant_email, subject, body)

    # --- Queue System ---

    async def queue_notification(self, notification_data: Dict[str, Any]) -> None:
        """Thread-safe add notification to queue for batch processing."""
        async with self._lock:
            notification_data = copy.deepcopy(notification_data)
            notification_data['queued_at'] = datetime.now().isoformat()
            self.notifications_queue.append(notification_data)
            self.logger.debug(f"Notification queued: {notification_data}")

    async def process_notification_queue(self) -> Dict[str, int]:
        """Process and send all queued notifications (thread-safe)."""
        processed = 0
        failed = 0
        async with self._lock:
            queue_copy = self.notifications_queue.copy()
            for notification in queue_copy:
                try:
                    notification_type = notification.get('type')
                    if notification_type == 'job_application':
                        success = await self.send_job_application_notification(
                            notification['employer_email'],
                            notification['job_title'],
                            notification['applicant_name']
                        )
                    elif notification_type == 'application_confirmation':
                        success = await self.send_application_confirmation(
                            notification['applicant_email'],
                            notification['job_title'],
                            notification['company_name']
                        )
                    elif notification_type == 'status_update':
                        success = await self.send_status_update(
                            notification['applicant_email'],
                            notification['job_title'],
                            notification['status'],
                            notification.get('message', '')
                        )
                    elif notification_type == 'custom_email':
                        success = await self.send_email(
                            notification['to_email'],
                            notification['subject'],
                            notification['body'],
                            notification.get('is_html', False)
                        )
                    else:
                        self.logger.warning(f"Unknown notification type: {notification_type}")
                        success = False

                    if success:
                        processed += 1
                        self.logger.info(f"Notification sent: {notification_type}")
                    else:
                        failed += 1
                        self.logger.error(f"Notification failed: {notification_type}")

                    self.notifications_queue.remove(notification)

                except Exception as e:
                    self.logger.error(f"Error processing notification: {e}")
                    failed += 1

        return {'processed': processed, 'failed': failed}

    async def send_bulk_notifications(self, notifications: List[Dict[str, Any]]) -> Dict[str, int]:
        """Send multiple notifications; returns count of sent/failed."""
        results = {'sent': 0, 'failed': 0}
        for notification in notifications:
            try:
                success = await self.send_email(
                    notification['email'],
                    notification['subject'],
                    notification['body'],
                    notification.get('is_html', False)
                )
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                self.logger.error(f"Bulk notification error: {e}")
                results['failed'] += 1
        return results

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and details."""
        return {
            'queue_length': len(self.notifications_queue),
            'oldest_notification': self.notifications_queue[0]['queued_at'] if self.notifications_queue else None,
            'queue_items': copy.deepcopy(self.notifications_queue)
        }

    # --- EXTENSIBILITY: add more notification channels here (SMS, Slack, etc) ---
    # def send_sms(self, ...): ...


# ========== Example Usage ==========
if __name__ == "__main__":
    import os
    import sys

    async def main():
        # Example: configure and send a test notification
        service = NotificationService()
        # Fill in your credentials here or use environment variables
        EMAIL = os.getenv('TEST_EMAIL') or 'your@email.com'
        PASSWORD = os.getenv('TEST_PASSWORD') or 'your_app_password'
        service.configure_email('smtp.gmail.com', 587, EMAIL, PASSWORD)
        await service.queue_notification({
            'type': 'job_application',
            'employer_email': EMAIL,
            'job_title': 'Python Developer',
            'applicant_name': 'Alice Doe'
        })
        result = await service.process_notification_queue()
        print("Processed:", result)

    # Run the example only if executed directly
    try:
        asyncio.run(main())
    except Exception as exc:
        print("Error:", exc)
        sys.exit(1)