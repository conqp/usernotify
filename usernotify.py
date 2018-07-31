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

from collections import namedtuple
from configparser import ConfigParser
from os import setuid, fork, wait, _exit
from pathlib import Path
from pwd import getpwnam
from subprocess import call


__all__ = ['MIN_UID', 'MAX_UID', 'Args', 'getuid', 'send', 'broadcast']


_DEFAULT_CONFIG = {
    'MIN_UID': 1000,
    'MAX_UID': 60000,
    'NOTIFY_SEND': '/usr/bin/notify-send',
    'RUN_USER': '/run/user'}
_SECTION_NAME = 'UserNotify'

# Load configurations.
_CONFIG = ConfigParser()
_CONFIG.setdefault(_SECTION_NAME, _DEFAULT_CONFIG)
_CONFIG.read('/etc/usernotify.ini')
_USER_CONFIG = ConfigParser()
_USER_CONFIG.read(Path.home().joinpath('.usernotify.conf'))
_CONFIG.update(_USER_CONFIG)
_SECTION = _CONFIG[_SECTION_NAME]

# Read configuration values.
MIN_UID = int(_CONFIG.get(_SECTION_NAME, 'MIN_UID'))
MAX_UID = int(_SECTION['MAX_UID'])
_NOTIFY_SEND = _SECTION['NOTIFY_SEND']
_RUN_USER = Path(_SECTION['RUN_USER'])
_DBUS_BUS_DIR = '{}/bus'
_DBUS_PATH = _RUN_USER.joinpath(_DBUS_BUS_DIR)
_ENV = f'DBUS_SESSION_BUS_ADDRESS=unix:path={_DBUS_PATH}'
_DBUS_BUS_GLOB = _DBUS_BUS_DIR.format('*')
_UIDS = range(MIN_UID, MAX_UID + 1)


def _command_elements(uid, args):
    """Yields the respective string arguments."""

    yield _ENV.format(uid)
    yield _NOTIFY_SEND

    if args.urgency:
        yield f'--urgency={args.urgency}'

    if args.expire_time:
        yield f'--expire-time={args.expire_time}'

    if args.app_name:
        yield f'--app-name="{args.app_name}"'

    if args.icon:
        yield f'--icon="{args.icon}"'

    if args.category:
        yield f'--category={args.category}'

    if args.hint:
        yield f'--hint={args.hint}'

    if args.version:
        yield f'--version={args.version}'

    yield f'"{args.summary}"'

    if args.body:
        yield f'"{args.body}"'


def getuid(user):
    """Gets the UID for the respective user"""

    try:
        return int(user)
    except ValueError:
        return getpwnam(user).pw_uid


def send(uid, args):
    """Sends a notification to the respective user"""

    if fork() == 0:
        setuid(uid)
        _exit(call(' '.join(_command_elements(uid, args)), shell=True))

    _, returncode = wait()
    return returncode


def broadcast(cmd, uids=_UIDS):
    """Seds the respective message to all
    users with an active DBUS session.
    """

    returncode = 0

    for path in _RUN_USER.glob(_DBUS_BUS_GLOB):
        uid = int(path.parent.name)

        if uid in uids:
            returncode += send(uid, cmd)

    return returncode


class Args(namedtuple('Args', (
        'summary', 'body', 'urgency', 'expire_time', 'app_name', 'icon',
        'category', 'hint', 'version'))):
    """Arguments for nofiy-send."""

    __slots__ = ()

    @classmethod
    def from_options(cls, options):
        """Creates arguments from the respective docopt options."""
        return cls(
            options['<summary>'], options['<body>'], options['--urgency'],
            options['--expire-time'], options['--app-name'], options['--icon'],
            options['--category'], options['--hint'], options['--version'])
