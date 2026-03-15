"""
Auto Email Sender for Cold Outreach
Run separately from the main app: python3 email_sender.py
Sends emails with random delays (10-60 seconds) to avoid spam filters.
"""
import smtplib
import json
import os
import time
import random
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "email_config.json")
QUEUE_PATH = os.path.join(DATA_DIR, "email_queue.json")
LOG_PATH = os.path.join(DATA_DIR, "email_log.json")

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def send_email(smtp_config, to_email, to_name, subject, body, from_name):
    """Send a single email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_config['email']}>"
    msg["To"] = to_email

    # Plain text version
    msg.attach(MIMEText(body, "plain"))

    # Connect and send
    if smtp_config["provider"] == "gmail":
        server = smtplib.SMTP("smtp.gmail.com", 587)
    elif smtp_config["provider"] == "outlook":
        server = smtplib.SMTP("smtp.office365.com", 587)
    elif smtp_config["provider"] == "yahoo":
        server = smtplib.SMTP("smtp.mail.yahoo.com", 587)
    else:
        server = smtplib.SMTP(smtp_config.get("smtp_host", "smtp.gmail.com"),
                              int(smtp_config.get("smtp_port", 587)))

    server.ehlo()
    server.starttls()
    server.login(smtp_config["email"], smtp_config["password"])
    server.sendmail(smtp_config["email"], to_email, msg.as_string())
    server.quit()

def fill_template(template, replacements):
    """Replace [placeholders] in template with actual values."""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"[{key}]", str(value))
    return result

def process_queue():
    """Process the email queue with random delays."""
    config = load_json(CONFIG_PATH, {})
    queue = load_json(QUEUE_PATH, [])
    log = load_json(LOG_PATH, [])

    if not config.get("email") or not config.get("password"):
        print("ERROR: Email not configured. Run the setup in the dashboard first.")
        print(f"Config file: {CONFIG_PATH}")
        return

    if not queue:
        print("No emails in queue.")
        return

    pending = [e for e in queue if e.get("status") == "queued"]
    if not pending:
        print("No pending emails to send.")
        return

    print(f"\n{'='*60}")
    print(f"EMAIL SENDER - {len(pending)} emails to send")
    print(f"Sending from: {config['email']}")
    print(f"Random delay: 10-60 seconds between emails")
    print(f"{'='*60}\n")

    sent_count = 0
    error_count = 0

    for i, email in enumerate(pending):
        try:
            print(f"[{i+1}/{len(pending)}] Sending to: {email['to_email']} ({email.get('entity', 'Unknown')})")

            send_email(
                smtp_config=config,
                to_email=email["to_email"],
                to_name=email.get("to_name", ""),
                subject=email["subject"],
                body=email["body"],
                from_name=config.get("from_name", "")
            )

            # Update queue status
            email["status"] = "sent"
            email["sent_at"] = datetime.now().isoformat()
            sent_count += 1

            # Log it
            log.append({
                "to_email": email["to_email"],
                "to_name": email.get("to_name", ""),
                "entity": email.get("entity", ""),
                "subject": email["subject"],
                "sent_at": datetime.now().isoformat(),
                "status": "sent"
            })

            print(f"  SENT successfully")

            # Random delay before next email (10-60 seconds)
            if i < len(pending) - 1:
                delay = random.randint(10, 60)
                print(f"  Waiting {delay} seconds before next email...")
                time.sleep(delay)

        except Exception as e:
            email["status"] = "error"
            email["error"] = str(e)
            error_count += 1

            log.append({
                "to_email": email["to_email"],
                "entity": email.get("entity", ""),
                "subject": email["subject"],
                "sent_at": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            })

            print(f"  ERROR: {e}")

    # Save updated queue and log
    save_json(QUEUE_PATH, queue)
    save_json(LOG_PATH, log)

    print(f"\n{'='*60}")
    print(f"COMPLETE: {sent_count} sent, {error_count} errors")
    print(f"{'='*60}")

def setup_config():
    """Interactive setup for email configuration."""
    print("\n=== EMAIL CONFIGURATION ===\n")
    print("Choose your email provider:")
    print("  1. Gmail (requires App Password)")
    print("  2. Outlook/Office 365")
    print("  3. Yahoo")
    print("  4. Custom SMTP")

    choice = input("\nSelect (1-4): ").strip()
    providers = {"1": "gmail", "2": "outlook", "3": "yahoo", "4": "custom"}
    provider = providers.get(choice, "gmail")

    email = input("Your email address: ").strip()
    password = input("App Password (NOT your regular password): ").strip()
    from_name = input("Your name (as it appears in emails): ").strip()
    company = input("Company name: ").strip()

    config = {
        "provider": provider,
        "email": email,
        "password": password,
        "from_name": from_name,
        "company": company,
    }

    if provider == "custom":
        config["smtp_host"] = input("SMTP host: ").strip()
        config["smtp_port"] = input("SMTP port: ").strip()

    save_json(CONFIG_PATH, config)
    print(f"\nConfig saved to {CONFIG_PATH}")
    print("\nIMPORTANT: For Gmail, you need an App Password:")
    print("  1. Go to myaccount.google.com > Security > 2-Step Verification")
    print("  2. Scroll to 'App passwords' at the bottom")
    print("  3. Generate a new app password for 'Mail'")
    print("  4. Use THAT password (not your Gmail password)")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_config()
    elif len(sys.argv) > 1 and sys.argv[1] == "send":
        process_queue()
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        queue = load_json(QUEUE_PATH, [])
        log = load_json(LOG_PATH, [])
        queued = len([e for e in queue if e["status"] == "queued"])
        sent = len([e for e in queue if e["status"] == "sent"])
        errors = len([e for e in queue if e["status"] == "error"])
        print(f"Queue: {queued} pending | {sent} sent | {errors} errors")
        print(f"Total emails logged: {len(log)}")
    else:
        print("Usage:")
        print("  python3 email_sender.py setup   - Configure email credentials")
        print("  python3 email_sender.py send    - Send all queued emails")
        print("  python3 email_sender.py status  - Check queue status")
