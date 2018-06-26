#    usernotify - Wrapper library for notify-send.
#    Copyright (C) 2018  Richard Neumann
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""A notify-send wrapping library."""

from os import setuid, fork, wait, _exit
from pathlib import Path
from pwd import getpwnam
from subprocess import call

__all__ = ['MIN_UID', 'MAX_UID', 'getuid', 'send', 'send_all']


MIN_UID = 1000
MAX_UID = 60000
_NOTIFY_SEND = '/usr/bin/notify-send'
_RUN_USER = Path('/run/user')
_DBUS_BUS_DIR = '{}/bus'
_DBUS_PATH = _RUN_USER.joinpath(_DBUS_BUS_DIR)
_ENV = f'DBUS_SESSION_BUS_ADDRESS=unix:path={_DBUS_PATH}'
_DBUS_BUS_GLOB = _DBUS_BUS_DIR.format('*')
_UIDS = range(MIN_UID, MAX_UID + 1)


def _mkcmd(uid, summary, body=None, urgency=None, expire_time=None,
           app_name=None, icon=None, category=None, hint=None, version=None):
    """Sends a notification to the respective user"""

    yield _ENV.format(uid)
    yield _NOTIFY_SEND

    if urgency:
        yield f'--urgency={urgency}'

    if expire_time:
        yield f'--expire-time={expire_time}'

    if app_name:
        yield f'--app-name="{app_name}"'

    if icon:
        yield f'--icon="{icon}"'

    if category:
        yield f'--category={category}'

    if hint:
        yield f'--hint={hint}'

    if version:
        yield f'--version={version}'

    yield f'"{summary}"'

    if body:
        yield f'"{body}"'


def getuid(user):
    """Gets the UID for the respective user"""

    try:
        return int(user)
    except ValueError:
        return getpwnam(user).pw_uid


def send(uid, summary, body=None, urgency=None, expire_time=None,
         app_name=None, icon=None, category=None, hint=None, version=None):
    """Sends a notification to the respective user"""

    cmd = ' '.join(_mkcmd(
        uid, summary, body=body, urgency=urgency, expire_time=expire_time,
        app_name=app_name, icon=icon, category=category, hint=hint,
        version=version))

    if fork() == 0:
        setuid(uid)
        _exit(call(cmd, shell=True))

    _, returncode = wait()
    return returncode


def send_all(summary, body=None, urgency=None, expire_time=None, app_name=None,
             icon=None, category=None, hint=None, version=None, uids=_UIDS):
    """Seds the respective message to all
    users with an active DBUS session.
    """

    returncode = 0

    for path in _RUN_USER.glob(_DBUS_BUS_GLOB):
        uid = int(path.parent.name)

        if uid in uids:
            returncode += send(
                uid, summary, body=body, urgency=urgency,
                expire_time=expire_time, app_name=app_name, icon=icon,
                category=category, hint=hint, version=version)

    return returncode
