import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_price_drop_alert(product_name, old_price, new_price, url):
    host = os.getenv('EMAIL_HOST')
    port = int(os.getenv('EMAIL_PORT', 587))
    user = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    to_addr = os.getenv('EMAIL_TO')
    if not all([host, port, user, password, to_addr]):
        print('Email credentials not fully set in environment variables.')
        return
    subject = f"Price Drop Alert: {product_name}"
    body = f"The price for {product_name} has dropped from ${old_price} to ${new_price}.\n\nProduct link: {url}"
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to_addr, msg.as_string())
        print(f"Price drop alert sent for {product_name}")
    except Exception as e:
        print(f"Failed to send email: {e}") 