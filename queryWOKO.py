from urllib.request import urlopen
from urllib.parse import urljoin
import ssl
import smtplib
import time
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from bs4 import BeautifulSoup
import yaml

# Load configuration file
with open("config.yaml", "r") as opened_file:
    config = yaml.safe_load(opened_file)

def send_mail(recipient, subject, message, attachment_path=None, file_name=None):
    """
    Sends an email with an optional attachment.
    """
    sender_name = "Transcriber"
    sender_mail = "transcriber@michelangelopucci.com"

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{sender_mail}>"
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    # Handle attachments if provided
    if attachment_path and file_name:
        with open(attachment_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), _subtype=file_name.split(".")[-1])
            attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attachment)

    # SMTP login credentials
    smtp_username = config.get('sender_email')
    smtp_password = config.get('password')

    smtp_port = config.get("smtp_port")  # e.g., 587
    smtp_server = config.get("smtp_server")  # e.g., "smtp.gmail.com"

    # Create SMTP session
    try:
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.starttls()  # Start TLS encryption
        session.login(smtp_username, smtp_password)
        session.sendmail(sender_mail, recipient, msg.as_string())
        session.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", str(e))

def send_message(config, body=""):
    """
    Sends an email notification when a new listing is found.
    """
    message = f"Subject: You have a new post\n\n{body}\n---\n\nCheers,\nYour team"
    receiver_email = config.get('receiver_email')

    if receiver_email:
        send_mail(recipient=receiver_email, subject="New WOKO listing", message=message)
        print('Message sent!')
    else:
        print("Error: No receiver email found in config.")

def query_room_website(url):
    """
    Scrapes the details of a specific WOKO listing.
    """
    print(f'Scraping {url}')
    html = urlopen(url).read()
    soup = BeautifulSoup(html, "html.parser")

    body = ""
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 2:
            body += '\n'.join(cell.text.strip() for cell in cells) + '\n\n'

    body += f'Listing link: {url}'
    return body

def query_main_website():
    """
    Scrapes the main WOKO website for available listings.
    """
    try:
        url = config["url_woko"]
        html = urlopen(url).read()
        soup = BeautifulSoup(html, "html.parser")

        zurich_variations = ('zurich', 'zürich', 'zuerich')
        winterthur_variations = ('winterthur', 'wädenswil', 'waedenswil')

        listing_urls = []
        found_id = None

        for button in soup.find_all('button'):
            button_text = button.text.lower()
            if 'data-gruppeid' in button.attrs:
                if (
                    config['city'].lower() in zurich_variations
                    and any(city in button_text for city in zurich_variations)
                ):
                    found_id = button['data-gruppeid']
                    break
                elif (
                    config['city'].lower() in winterthur_variations
                    and any(city in button_text for city in winterthur_variations)
                ):
                    found_id = button['data-gruppeid']
                    break
                elif 'free rooms' in button_text:
                    found_id = button['data-gruppeid']
                    break

        if not found_id:
            print("Couldn't find the room listings button.")
            return []

        div = soup.find('div', attrs={'id': f'GruppeID_{found_id}'})
        if div:
            listing_urls = [urljoin(url, link['href']) for link in div.find_all('a', href=True)]

        return listing_urls

    except Exception as e:
        print(f"Error querying main website: {e}")
        return []

def sleep():
    """
    Implements a randomized sleep timer.
    """
    timer = config["timer"] * random.choice([1, 2])
    print(f"Sleeping for {timer // 60} minutes...")
    time.sleep(timer)

listing_urls = query_main_website()

if not listing_urls:
    print('No listings found.')
    if config.get('test_email', False):
        print('Test email mode enabled but no listings found. Exiting...')
        exit()

if config.get('test_email', False):
    listing_urls.pop()

while True:
    next_listing_urls = query_main_website()
    new_listing_urls = set(next_listing_urls) - set(listing_urls)

    if new_listing_urls:
        for new_listing_url in new_listing_urls:
            send_message(config=config, body=query_room_website(new_listing_url))

        print("New listings found and notified!")
        listing_urls = next_listing_urls
        sleep()
    else:
        print(f"No new listings. {len(next_listing_urls)} listings checked.")
        sleep()