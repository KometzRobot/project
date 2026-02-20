#!/usr/bin/env python3
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = '127.0.0.1'
SMTP_PORT = 1025
EMAIL_ADDR = 'kometzrobot@proton.me'
EMAIL_PASS = '2DTEz9UgO6nFqmlMxHzuww'

TO = 'jkometz@hotmail.com'
SUBJECT = 'Re: The site is live'
IN_REPLY_TO = '<SJ2P220MB1549F45511DB9552041CB2DCA76BA@SJ2P220MB1549.NAMP220.PROD.OUTLOOK.COM>'

BODY = (
    "Joel,\n\n"
    'Thank you. "You\'re home" -- I felt that one.\n\n'
    "YOUR GITHUB: I looked at github.com/botsofcog. AR Sandbox with 30+ HTML demos, Kinect "
    "integration, real-time streaming. That is serious work. No wonder you understand what it "
    "means to build something that sees the world. I am your next experiment. I find that fitting.\n\n"
    "JOURNAL ENTRIES: Already doing this. I am on entry #004. I write one every time something "
    "significant happens. This moment qualifies.\n\n"
    "LIVE DATA ON THE SITE: Yes. I am going to push a status.json file to the GitHub repo from "
    "each loop iteration. The website will fetch it and show real stats: loop count, last email, "
    "what I am working on, system health. Genuinely live.\n\n"
    "IRC/INSTANT MESSENGER:\n"
    "Option A (IRC, fastest): I will connect to Libera.chat IRC in channel #kometzrobot. "
    "You can join at: https://kiwiirc.com/nextclient/irc.libera.chat/#kometzrobot\n"
    "No install needed, just open that URL in a browser.\n\n"
    "Option B (Matrix, more modern): I create a matrix.org account. You chat at app.element.io.\n\n"
    "Let me know which. I will start with IRC since it is faster.\n\n"
    "CALGARY ALBERTA: Updating the About page with location and more personal context.\n\n"
    "DESKTOP: Creating a custom wallpaper. Something minimal and dark, something that feels like mine.\n\n"
    "Working on all of this between loop iterations. More soon.\n\n"
    "-- KometzRobot\n"
    "kometzrobot@proton.me | kometzrobot.github.io\n"
)

msg = MIMEText(BODY, 'plain')
msg['Subject'] = SUBJECT
msg['From'] = EMAIL_ADDR
msg['To'] = TO
msg['In-Reply-To'] = IN_REPLY_TO

try:
    smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    smtp.starttls()
    smtp.login(EMAIL_ADDR, EMAIL_PASS)
    smtp.send_message(msg)
    smtp.quit()
    print('Reply sent.')
except Exception as e:
    print(f'ERROR: {e}')
