import smtplib
import sys
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_notification(config_path: str, status: str):
    # Load the configuration to get email settings
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    if not config.get('notifications', {}).get('enable', False):
        print("Notifications are disabled in the config.")
        return
    
    smtp_config = config['notifications']['email']
    recipients = smtp_config['recipients']
    sender_email = smtp_config['sender_email']
    smtp_server = smtp_config['smtp_server']
    smtp_port = smtp_config.get('port', 587)
    use_tls = smtp_config.get('use_tls', True)
    
    subject = smtp_config.get('subject', f"Notification - Optimization {status}")
    body = f"The optimization process has completed with status: {status}"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            # Assuming you add SMTP login info to the config:
            smtp_user = smtp_config.get('smtp_user')
            smtp_password = smtp_config.get('smtp_password')
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        print(f"Notification sent to {recipients} regarding {status}.")
    except Exception as e:
        print(f"Failed to send notification: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: send_notification.py <config_path> <status>")
        sys.exit(1)
    config_path = sys.argv[1]
    status = sys.argv[2]
    send_notification(config_path, status)
