import os
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
# These are fetched from GitHub Secrets in production
GMAIL_USER = os.getenv('GMAIL_USER', 'saban.productions00@gmail.com')
GMAIL_PASS = os.getenv('GMAIL_PASS', 'zouw kiep ubqs dbof')
FIREBASE_URL = os.getenv('FIREBASE_URL', 'https://githubemail-s-default-rtdb.firebaseio.com/')
FIREBASE_TOKEN = os.getenv('FIREBASE_TOKEN', 'jBUMghKKe6tdHhpDRaTWLTRXPa6Gk90W5aootP4e')

def get_firebase_data(path):
    """Fetch data from Firebase RTDB using REST API."""
    # Ensure the URL is properly formatted
    base_url = FIREBASE_URL.rstrip('/')
    url = f"{base_url}/{path}.json?auth={FIREBASE_TOKEN}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching {path}: {response.status_code} - {response.text}")
        return None
    return response.json()

def update_prospect_status(prospect_id, status):
    """Update prospect status in Firebase to 'sent' or 'failed'."""
    base_url = FIREBASE_URL.rstrip('/')
    url = f"{base_url}/prospects/{prospect_id}.json?auth={FIREBASE_TOKEN}"
    
    response = requests.patch(url, json={"status": status})
    return response.status_code == 200

def send_email(to_email, subject, html_content):
    """Send HTML email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach the HTML content
    msg.attach(MIMEText(html_content, 'html'))

    # Connect to Gmail SMTP server
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

def main():
    print("🚀 Starting Cold Email Outreach Bot...")
    
    try:
        # 1. Fetch Campaign Settings
        print("Fetching campaign settings...")
        campaign = get_firebase_data('campaign')
        if not campaign:
            print("❌ No campaign settings found. Please configure subject and template in dashboard.")
            return

        subject = campaign.get('subject', 'No Subject')
        template = campaign.get('template', '')
        delay = int(campaign.get('delay', 30))

        if not template:
            print("❌ Email template is empty. Exiting.")
            return

        # 2. Fetch Prospects
        print("Fetching prospects...")
        prospects = get_firebase_data('prospects')
        if not prospects:
            print("❌ No prospects found in database.")
            return

        # 3. Filter pending prospects
        pending = {k: v for k, v in prospects.items() if v.get('status') == 'pending'}
        
        if not pending:
            print("✅ All emails have been sent! No pending prospects.")
            return

        print(f"📋 Found {len(pending)} pending prospects. Starting delivery...")

        # 4. Process each prospect
        for p_id, p_data in pending.items():
            name = p_data.get('name', 'there')
            email = p_data.get('email')

            if not email:
                print(f"⚠️ Skipping {p_id} (missing email address)")
                continue

            print(f"📧 Sending to: {name} <{email}>")

            # Personalize the HTML template
            personalized_body = template.replace('{{name}}', name)

            try:
                send_email(email, subject, personalized_body)
                print(f"   ✅ Sent successfully!")
                
                # Update status in Firebase
                if update_prospect_status(p_id, 'sent'):
                    print(f"   💾 Database updated.")
                else:
                    print(f"   ⚠️ Failed to update database for {email}")

            except Exception as e:
                print(f"   ❌ Failed to send to {email}: {e}")
                update_prospect_status(p_id, 'failed')
                continue

            # Wait before next email to avoid spam filters
            if p_id != list(pending.keys())[-1]:
                print(f"⏱️ Waiting {delay} seconds...")
                time.sleep(delay)

        print("\n🎉 Campaign delivery finished!")

    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    main()
