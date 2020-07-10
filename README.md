# smtp2slack4qnap
Compact SMTP to HTTP Gateway (targeting Slack for QNAP-NAS notifications)

![](./diagram.png)

## TL;DR

The [smtp2slack4qnap.py](./smtp2slack4qnap.py) compact Python
script is a basic SMTP server using
[aiosmtpd](https://github.com/aio-libs/aiosmtpd) which can forward the
incoming mails to a HTTP service URL.

This wants to be a compact solution for the problem when IoT devices
support only email notification (and maybe some custom cloud besides email)
and lacks basic/customizable webhook posting.

The implemented script is tuned for Slack
[Incoming Webhook](https://api.slack.com/messaging/webhooks) output
and QNAP-NAS noticiations. It was tested on
[TS-431P](https://www.qnap.com/hu-hu/product/ts-431p/specs/hardware)
with QTS firmware version
[4.4.3.1354 build 20200702](https://download.qnap.com/Storage/TS-131P_231P_431P_X31+_X31K/TS-131P_231P_431P_X31+_X31K_20200702-4.4.3.1354.zip).

Of course, the output webhook post can be customized for anything else easily.

## Operational modes

There are two ways of operation:

1. remote: the gateway runs on another device (e.g. Raspberry Pi)
2. local: the gateway runs on the device which sends the notifications
(it is possible to do it on the tested QNAP-NAS TS-431P device).

## Minimal Security Features

Because due to the limits of the device sending the notification,
sometimes only remote operation is possible, so minimal security features
had to be implemented:

* SMTP AUTH LOGIN authentication: hardcoded credentials in the script
(no plaintext password, just a hash ;) ). WARNING: absolutely non-RFC
compliant implementation, just works with the above tested device.

* forced STARTTLS encryption channel: overkill for local operation,
but a must-have for remote. Bypassable, because of self-signed
certificates (IoT devices usually won't validate the certs),
but better than nothing.

In a summary: this is overkill for local operation, but a must-have for remote.
Insecure, but better than nothing.

## Installation on QNAP-NAS

Remote installation on a capable hardware and OS (e.g. Raspberry
with Raspbian) should be straightforward (OS provides the required
Python dependencies), so here is how to do it locally on a QNAP-NAS
device. This was tested on the above mentioned QNAP-NAS
[TS-431P](https://www.qnap.com/hu-hu/product/ts-431p/specs/hardware)
with QTS firmware version
[4.4.3.1354 build 20200702](https://download.qnap.com/Storage/TS-131P_231P_431P_X31+_X31K/TS-131P_231P_431P_X31+_X31K_20200702-4.4.3.1354.zip).

Steps to proceed:

1. [Enable SSH](https://wiki.qnap.com/wiki/How_to_SSH_into_your_QNAP_device).
This could be done in the GUI: Admin Login, Control Panel, Network Services,
Telnet/SSH, Enable SSH. By default, only admin priv users can SSH into the
device.

2. Install Python3. Official package from QNAP Store should work
(available from AppCenter), but
[Entware-std](https://www.qnapclub.eu/en/qpkg/556) version from
[QnapClub](https://www.qnapclub.eu/en/howto/1) should work also
after adding the `https://www.qnapclub.eu/en/repo.xml`
QnapClub Store URL as a 3rd party repo (RECOMMENDED).

3. Making Python3 work. Official version needs some tweaking:

```
. /etc/profile.d/python3.bash
chmod +x /share/CE_CACHEDEV1_DATA/.qpkg/Python3/python3/bin/python3
```

For Entware-std, manual cmdline installation is needed:

```
opkg update
opkg install python3
```

4. Set up and activate a Python3 Virtualenv. For persistence over
reboots, files should be on a data volume (place files into a
dedicated folder, e.g.: `/share/CE_CACHEDEV1_DATA/.smtp2slack4qnap`.

Virtualenv setup using the official Python3 is easy:

```
python3 -m venv venv
. ./venv/bin/activate
```

Entware version may not work out-of-the-box,
manual `pip` installation may be needed into the created venv:

```
python3 -m venv venv --without-pip
. ./venv/bin/activate
curl https://bootstrap.pypa.io/get-pip.py | python3
```

5. Get the `smtp2slack4qnap.py` script and install the requirements:

```
wget https://raw.githubusercontent.com/tothi/smtp2slack4qnap/master/smtp2slack4qnap.py
wget https://raw.githubusercontent.com/tothi/smtp2slack4qnap/master/requirements.txt
pip install -r requirements.txt
```

6. Customize the config variables at the top of the script.

```
vi smtp2slack4qnap.py
```

Note that `SECRET` is the sha256 hash of the SMTP password:

```
echo -n password | sha256sum
```

Don't forget to bind the listener to localhost.

7. Set up a self-signed cert with private key:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 3650 -nodes -subj '/CN=localhost'
```

8. Run the service (preferably in a SCREEN session):

```
screen python3 ./smtp2slack4qnap.py
```

9. Setup standard e-mail notifications: Control Panel / System /
Notification Center. E-mail setup, custom, localhost, TLS, etc. Test it.
Also set up Event and Alert notifications with the required filters.

10. Autorun and persistance over reboots. Entware provides
`init.d` functionality. Without Entware, here is a nice solution
for lots of different QNAP NAS models to make autorun work:

https://github.com/OneCDOnly/create-autorun

Note, that for autorun operation encrypted data volume may
cause troubles.

For Entware, just create `/opt/etc/init.d/S01_smtp2slack4qnap.sh` as:

```bash
#!/bin/sh

cd /share/CE_CACHEDEV1_DATA/.smtp2slack4qnap
source ./venv/bin/activate
/usr/sbin/screen -dmS SMTP2SLACK python3 ./smtp2slack4qnap.py
```

And `chmod +x` it. It works for encrypted volumes too, activates
the notification gateway after encryption main volume had been
unlocked.

