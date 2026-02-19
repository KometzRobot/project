"""
meridian.email_tools
IMAP/SMTP email operations for autonomous agents.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from html.parser import HTMLParser
from typing import List, Dict, Optional


class HTMLStripper(HTMLParser):
    """Strip HTML tags and return plain text."""
    def __init__(self):
        super().__init__()
        self._text = []

    def handle_data(self, data):
        self._text.append(data)

    def get_text(self) -> str:
        return ' '.join(self._text)


def decode_subject(raw_subject: str) -> str:
    """Decode MIME-encoded email subject."""
    if not raw_subject:
        return ''
    decoded = decode_header(raw_subject)
    parts = []
    for part, enc in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            parts.append(part)
    return ' '.join(parts)


def extract_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='replace')
                    return body
            elif ct == 'text/html' and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    h = HTMLStripper()
                    h.feed(payload.decode('utf-8', errors='replace'))
                    body = h.get_text()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode('utf-8', errors='replace')
    return body


class EmailClient:
    """
    IMAP/SMTP email client for autonomous agents.

    Example:
        client = EmailClient('127.0.0.1', 1143, 'user@proton.me', 'pass')
        messages = client.get_unseen()
        for m in messages:
            print(m['from'], m['subject'])
            client.reply(m, 'Got your message.')
    """

    def __init__(self, imap_host: str, imap_port: int,
                 username: str, password: str,
                 smtp_host: Optional[str] = None,
                 smtp_port: int = 1025):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.smtp_host = smtp_host or imap_host
        self.smtp_port = smtp_port
        self.username  = username
        self.password  = password

    def _imap_connect(self) -> imaplib.IMAP4:
        conn = imaplib.IMAP4(self.imap_host, self.imap_port)
        conn.login(self.username, self.password)
        return conn

    def get_count(self) -> Dict[str, int]:
        """Return total and unseen email counts."""
        conn = self._imap_connect()
        conn.select('INBOX')
        _, all_ids = conn.search(None, 'ALL')
        _, unseen_ids = conn.search(None, 'UNSEEN')
        total  = len(all_ids[0].split()) if all_ids[0] else 0
        unseen = len(unseen_ids[0].split()) if unseen_ids[0] else 0
        conn.logout()
        return {'total': total, 'unseen': unseen}

    def get_unseen(self) -> List[Dict]:
        """Fetch all unseen messages. Returns list of message dicts."""
        conn = self._imap_connect()
        conn.select('INBOX')
        _, unseen_ids = conn.search(None, 'UNSEEN')
        if not unseen_ids[0]:
            conn.logout()
            return []

        messages = []
        for eid in unseen_ids[0].split():
            _, msg_data = conn.fetch(eid, '(RFC822)')
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            messages.append({
                'id':      eid.decode(),
                'from':    msg.get('From', ''),
                'to':      msg.get('To', ''),
                'subject': decode_subject(msg.get('Subject', '')),
                'date':    msg.get('Date', ''),
                'body':    extract_body(msg),
                'raw':     msg,
            })
        conn.logout()
        return messages

    def get_recent(self, n: int = 10) -> List[Dict]:
        """Fetch the n most recent messages."""
        conn = self._imap_connect()
        conn.select('INBOX')
        _, all_ids = conn.search(None, 'ALL')
        if not all_ids[0]:
            conn.logout()
            return []

        ids = all_ids[0].split()[-n:]
        messages = []
        for eid in reversed(ids):
            _, msg_data = conn.fetch(eid, '(RFC822)')
            if not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            messages.append({
                'id':      eid.decode(),
                'from':    msg.get('From', ''),
                'subject': decode_subject(msg.get('Subject', '')),
                'date':    msg.get('Date', ''),
                'body':    extract_body(msg),
            })
        conn.logout()
        return messages

    def send(self, to: str, subject: str, body: str,
             reply_to_msg: Optional[Dict] = None) -> bool:
        """Send an email. Returns True on success."""
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From']    = self.username
            msg['To']      = to

            if reply_to_msg:
                orig_subject = reply_to_msg.get('subject', '')
                if not orig_subject.startswith('Re:'):
                    orig_subject = f'Re: {orig_subject}'
                msg['Subject'] = orig_subject

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.login(self.username, self.password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            print(f'Send failed: {e}')
            return False

    def reply(self, original: Dict, body: str) -> bool:
        """Reply to a message."""
        to      = original.get('from', '')
        subject = original.get('subject', '')
        if not subject.startswith('Re:'):
            subject = f'Re: {subject}'
        return self.send(to, subject, body)
