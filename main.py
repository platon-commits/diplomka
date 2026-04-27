import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'mnogonat')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))

LAST_ID_FILE = 'last_id.txt'

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN or CHAT_ID not set.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Message sent successfully.")
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_last_seen_id():
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, 'r') as f:
                return int(f.read().strip())
        except ValueError:
            return 0
    return 0

def save_last_seen_id(msg_id):
    with open(LAST_ID_FILE, 'w') as f:
        f.write(str(msg_id))

def extract_brief(text, limit=300):
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(' ', 1)[0] + "..."

def check_channel():
    url = f"https://t.me/s/{TARGET_CHANNEL}"
    print(f"Checking {url}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    messages = soup.find_all(class_='tgme_widget_message')
    
    last_seen_id = get_last_seen_id()
    new_last_id = last_seen_id
    
    new_messages = []

    for msg in messages:
        # Get Message ID
        # data-post="channelname/123"
        data_post = msg.get('data-post')
        if not data_post:
            continue
            
        try:
            msg_id = int(data_post.split('/')[-1])
        except ValueError:
            continue

        if msg_id > last_seen_id:
            # It's a new message
            text_div = msg.find(class_='tgme_widget_message_text')
            text_content = text_div.get_text(separator="\n", strip=True) if text_div else "[Media/Image]"
            
            # Simple deduplication just in case
            new_messages.append((msg_id, text_content))
            
            if msg_id > new_last_id:
                new_last_id = msg_id

    # Send new messages (sorted by ID to keep order)
    new_messages.sort(key=lambda x: x[0])
    
    for msg_id, content in new_messages:
        brief = extract_brief(content)
        link = f"https://t.me/{TARGET_CHANNEL}/{msg_id}"
        
        message_text = (
            f"**🔔 Update from {TARGET_CHANNEL}**\n\n"
            f"{brief}\n\n"
            f"[Read Full]({link})"
        )
        send_telegram_message(message_text)
        time.sleep(1) # Rate limit

    if new_last_id > last_seen_id:
        save_last_seen_id(new_last_id)
        print(f"Updated last seen ID to {new_last_id}")
    else:
        print("No new messages.")

def main():
    print(f"Starting Scraper for {TARGET_CHANNEL}...")
    print(f"Bot Token: {'*' * 5 if BOT_TOKEN else 'MISSING'}")
    print(f"Chat ID: {CHAT_ID if CHAT_ID else 'MISSING'}")
    
    while True:
        check_channel()
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
