from urllib.request import urlopen
from urllib.parse import urljoin
import ssl
import smtplib
import time
import random
from bs4 import BeautifulSoup
import yaml

with open("config.yaml", "r") as opened_file:
    config = yaml.safe_load(opened_file)


def send_mail(recipient, subject, message):
    # Email addresses
    sender_name = "Transcriber"
    sender_mail = "transcriber@michelangelopucci.com"

    # Create message object instance
    msg = MIMEMultipart()
    # Setup the parameters of the message
    msg['From'] = f"{sender_name} <{sender_mail}>"
    msg['To'] = recipient
    msg['Subject'] = subject

    # Add the message body to the email
    msg.attach(MIMEText(message, 'plain'))


    if not (attachment_path is None and file_name is None):
        with open(attachment_path, 'rb') as file:
            attachment = MIMEApplication(file.read(), _subtype=file_name.split(".")[-1])
            attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attachment)

    # Create SMTP session
    smtp_username = config.get('sender_email')
    smtp_password = config.get('password')

    smtp_port = config.get("smtp_port") # 587
    smtp_server = config.get("smtp_server") # "smtp.gmail.com"
    session = smtplib.SMTP_SSL(smtp_server, smtp_port)
    session.login(smtp_username, smtp_password)

    # Send the message
    session.sendmail(sender_mail, recipient, msg.as_string())

    # Close the SMTP session
    session.quit()

def send_message(config, body=""):
    """
    Send email
    :param body: the body of the email.
    :param receiver_email:
    :param sender_email:
    :param password: The app-password of the email.
    :return:
    """
    
    message = f"Subject: You have a new post\n\n\n{body}\n---\n\n\nCheers,\nYour team"
    receiver_email = config.get('receiver_email')
    send_mail(recipient=receiver_email, subject="New woko listing", message=message)
    print('Message sent!')


def query_room_website(url):
    print(f'Scraping {url}')
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    body = ""
    # "tr" is table row
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 2:
            for cell in cells:
                info = cell.text.strip()
                body += info + '\n'
            body += '\n'

    body += f'Listing link\n{url}'

    return body


def query_main_website() -> list:
    """
    Find all listings on the main WOKO website
    :return: list of listings
    """
    url = config["url_woko"]
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    listings = {}
    id = ''
    zurich_variations = ('zurich', 'zürich', 'zuerich')
    winterthur_variations = ('winterthur', 'wädenswil', 'waedenswil')
    for button in soup.find_all('button'):
        button_text = button.text.lower()
        # The button and div containing the listing are linked with a data-gruppeid number.
        if 'data-gruppeid' in str(button):
            # Looking for the button corresponding to a specific city.
            if (
                    config['city'].lower() in zurich_variations
                    and any(city in button_text for city in zurich_variations)
            ):
                id = button['data-gruppeid']
                break

            elif (
                    config['city'].lower() in winterthur_variations
                    and any(city in button_text for city in winterthur_variations)
            ):
                id = button['data-gruppeid']
                break

            elif 'free rooms' in button_text:
                id = button['data-gruppeid']
                break

    if id == '':
        print("Couldn't find the room buttons")
        return listings

    # This is the div which the button reveals
    div = soup.find('div', attrs={'id': f'GruppeID_{id}'})

    listing_urls = []
    for link in div.find_all('a'):
        relative_room_url = link['href']
        room_url = urljoin(url, relative_room_url)
        listing_urls.append(room_url)

    return listing_urls


def sleep():
    """
    Sleep time
    :return:
    """
    timer = config["timer"] * random.choice([1, 2])
    print(f"Sleep for: {timer // 60}min.")
    time.sleep(timer)


listing_urls = query_main_website()

if len(listing_urls) == 0:
    print('No listings found')
    if config['test_email']:
        print('Cannot test without any listings, exiting')
        exit()

if config['test_email']:
    listing_urls.pop()

while True:
    next_listing_urls = query_main_website()

    new_listing_urls = set(next_listing_urls) - set(listing_urls)

    if new_listing_urls:
        for new_listing_url in new_listing_urls:
            send_message(
                body=query_room_website(new_listing_url),
                config=config,
            )
        print("Found!")
        listing_urls = next_listing_urls
        sleep()
    else:
        print(f"Still: {len(next_listing_urls)} rooms...")
        sleep()
