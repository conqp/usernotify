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
from configparser import Error, ConfigParser
from functools import lru_cache
from logging import basicConfig, getLogger
from os import setuid
from pathlib import Path
from pwd import getpwnam
from subprocess import Popen


__all__ = ['MIN_UID', 'MAX_UID', 'send', 'broadcast', 'Args']


_LOG_FORMAT = '[%(levelname)s] %(name)s: %(message)s'
basicConfig(format=_LOG_FORMAT)
_LOGGER = getLogger(__file__)
_DBUS_ENV_VAR = 'DBUS_SESSION_BUS_ADDRESS'
_DEFAULT_CONFIG = {
    'MIN_UID': 1000,
    'MAX_UID': 60000,
    'NOTIFY_SEND': '/usr/bin/notify-send',
    'RUN_USER': '/run/user'}
_SECTION_NAME = 'UserNotify'

# Load global configurations.
_CONFIG = ConfigParser()
_CONFIG.setdefault(_SECTION_NAME, _DEFAULT_CONFIG)
_CONFIG_PATH = Path('/etc/usernotify.conf')

try:
    _CONFIG.read(_CONFIG_PATH)
except Error as error:
    _LOGGER.warning(error)

# Load user-dependent configuration.
_USER_CONFIG = ConfigParser()
_USER_CONFIG_PATH = Path.home().joinpath('.usernotify.conf')

try:
    _USER_CONFIG.read(_USER_CONFIG_PATH)
except Error as error:
    _LOGGER.warning(error)

_CONFIG.update(_USER_CONFIG)
_SECTION = _CONFIG[_SECTION_NAME]

# Read configuration values.
MIN_UID = int(_SECTION['MIN_UID'])
MAX_UID = int(_SECTION['MAX_UID'])
_NOTIFY_SEND = _SECTION['NOTIFY_SEND']
_RUN_USER = Path(_SECTION['RUN_USER'])
_DBUS_BUS_DIR = '{}/bus'
_DBUS_PATH = _RUN_USER.joinpath(_DBUS_BUS_DIR)
_DBUS_BUS_GLOB = _DBUS_BUS_DIR.format('*')
_DBUS_ENV_PATH = f'unix:path={_DBUS_PATH}'
_UIDS = range(MIN_UID, MAX_UID + 1)


def _getuid(user):
    """Gets the UID for the respective user."""

    try:
        return int(user)
    except ValueError:
        return getpwnam(user).pw_uid


@lru_cache()
def _cached_command(args):
    """Returns the command tuple for subprocess
    invocation and caches it.
    """

    return (_NOTIFY_SEND, *args.args)


def send(user, args):
    """Sends a notification to the respective user."""

    uid = _getuid(user)
    env = {_DBUS_ENV_VAR: _DBUS_ENV_PATH.format(uid)}
    return Popen(args.command, env=env, preexec_fn=lambda: setuid(uid)).wait()


def broadcast(args, uids=_UIDS):
    """Seds the respective message to all
    users with an active DBUS session.
    """

    returncode = 0

    for path in _RUN_USER.glob(_DBUS_BUS_GLOB):
        uid = int(path.parent.name)

        if uid in uids:
            returncode += send(uid, args)

    return returncode


class Args(namedtuple('Args', (
        'summary', 'body', 'urgency', 'expire_time', 'app_name', 'icon',
        'category', 'hint', 'version'))):
    """Arguments for notifiy-send."""

    __slots__ = ()

    @classmethod
    def create(cls, summary, body=None, urgency=None, expire_time=None,
               app_name=None, icon=None, category=None, hint=None,
               version=None):
        """Initailizes the namedtuple with optional arguments."""
        return cls(
            summary, body, urgency, expire_time, app_name, icon, category,
            hint, version)

    @classmethod
    def from_options(cls, options):
        """Creates arguments from the respective docopt options."""
        return cls(
            options['<summary>'],
            body=options['<body>'],
            urgency=options['--urgency'],
            expire_time=options['--expire-time'],
            app_name=options['--app-name'],
            icon=options['--icon'],
            category=options['--category'],
            hint=options['--hint'],
            version=options['--version'])

    @property
    def args(self):
        """Yields the command line arguments for notify-send."""
        if self.urgency is not None:
            yield '--urgency'
            yield self.urgency

        if self.expire_time is not None:
            yield '--expire-time'
            yield self.expire_time

        if self.app_name is not None:
            yield '--app-name'
            yield self.app_name

        if self.icon is not None:
            yield '--icon'
            yield self.icon

        if self.category is not None:
            yield '--category'
            yield self.category

        if self.hint is not None:
            yield '--hint'
            yield self.hint

        if self.version:    # Boolean switch.
            yield '--version'

        yield self.summary

        if self.body is not None:
            yield self.body

    @property
    def command(self):
        """Returns the command tuple for subprocess invocation."""
        return _cached_command(self)
