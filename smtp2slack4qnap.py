#!/usr/bin/env python3
#
# Compact SMTP to HTTP Gateway
#  -> targeting Slack for QNAP-NAS notifications
#

# generate self-signed cert (better than nothing):
# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 3650 -nodes -subj '/CN=localhost'

import ssl
import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as Server, syntax
from aiosmtpd.handlers import Debugging
from hashlib import sha256
from base64 import b64encode, b64decode
import requests
import email
import json
import html2text
import re
import os

### CONFIG DATA

# for SMTP AUTH LOGIN (SECRET = sha256(password) avoiding storing plaintext)
USER = 'username'
SECRET = '1c18f3a76a7ad787ee1d5aea573bd51db1e559b85bbc4a3228076442e9a0bc90'

# SMTP listener (set to localhost if running on QNAP device)
LHOST, LPORT = '192.168.0.50', 1025

# target slack authenticated webhook url (keep confidential!)
WEBHOOK_URL = 'https://hooks.slack.com/services/XXXXXXXXX/YYYYYYYYY/aaaaaaaaaaaaaaaaaaaaaaaa'

### END OF CONFIG DATA

# implemented LOGIN authentication (non-RFC compliant, works with QNAP-NAS)
# overkill for running locally, but mandatory for remote
class MyServer(Server):
    authenticated = False
    @syntax('AUTH LOGIN')
    async def smtp_AUTH(self, arg):
        if arg != 'LOGIN':
            await self.push('501 Syntax: AUTH LOGIN')
            return
        await self.push('334 VXNlcm5hbWU=') # b64('Username')
        username = await self._reader.readline()
        username = b64decode(username.rstrip(b'\r\n'))
        await self.push('334 UGFzc3dvcmQ=') # b64('Password')
        password = await self._reader.readline()
        password = b64decode(password.rstrip(b'\r\n'))
        if username.decode() == USER and sha256(password).hexdigest() == SECRET:
            self.authenticated = True
            print("[+] Authenticated")
            await self.push('235 2.7.0 Authentication successful')
        else:
            await self.push('535 Invalid credentials')

# requires STARTTLS
# again, overkill for running locally, but mandatory for remote
class MyController(Controller):
    def factory(self):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain('cert.pem', 'key.pem')
        return MyServer(self.handler, tls_context=context, require_starttls=True)

def email2text(data):
    body = email.message_from_bytes(data).get_payload()
    h = html2text.HTML2Text()
    h.ignore_tables = True
    return re.sub(r'\n\s*\n', '\n\n', h.handle(body))

class CustomHandler:
    async def handle_DATA(self, server, session, envelope):
        if not server.authenticated:
            return '500 Unauthenticated. Could not process your message'
        mail_from = envelope.mail_from
        data = envelope.content
        text = email2text(data)
        # tuned for slack, but can be anything else
        requests.post(WEBHOOK_URL, data={'payload': json.dumps({'username': mail_from, 'text': text})})
        print("[+] Alert sent: {}".format(text.encode()))
        return '250 OK'

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    handler = CustomHandler()
    controller = MyController(handler, hostname=LHOST, port=LPORT)
    controller.start()
    input('SMTP server is running. Press Return to stop server and exit.\n')
    controller.stop()
