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

from configparser import Error, ConfigParser
from logging import basicConfig, getLogger
from os import setuid
from pathlib import Path
from pwd import getpwnam
from subprocess import Popen


__all__ = [
    'MIN_UID',
    'MAX_UID',
    'send',
    'broadcast',
    'add_notify_send_args',
    'notify_send_args']


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


def send(user, args):
    """Sends a notification to the respective user."""

    uid = _getuid(user)
    env = {_DBUS_ENV_VAR: _DBUS_ENV_PATH.format(uid)}
    command = (_NOTIFY_SEND, *args)
    return Popen(command, env=env, preexec_fn=lambda: setuid(uid)).wait()


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


def add_notify_send_args(parser):
    """Adds arguments for notify-send to the parser."""

    parser.add_argument('summary', metavar='SUMMARY')
    parser.add_argument('body', nargs='?', metavar='BODY')
    parser.add_argument(
        '-u', '--urgency', metavar='LEVEL',
        help='Specifies the urgency level: (low, normal, critical)')
    parser.add_argument(
        '-t', '--expire-time', metavar='TIME',
        help='Specifies the timeout in milliseconds at which to expire the'
        ' notification')
    parser.add_argument(
        '-a', '--app-name', metavar='APP_NAME',
        help='Specifies the app name for the icon')
    parser.add_argument(
        '-i', '--icon', metavar='ICON[,ICON...]',
        help='Specifies an icon filename or stock icon to display')
    parser.add_argument(
        '-c', '--category', metavar='TYPE[,TYPE...]',
        help='Specifies the notification category')
    parser.add_argument(
        '-h', '--hint', metavar='TYPE:NAME:VALUE',
        help='Specifies basic extra data to pass: (int, double, string, byte)')
    parser.add_argument(
        '-v', '--version', action='store_true', help='Version of the package')


def notify_send_args(args):
    """Yields the command line arguments for notify-send."""

    if args.urgency is not None:
        yield '--urgency'
        yield args.urgency

    if args.expire_time is not None:
        yield '--expire-time'
        yield args.expire_time

    if args.app_name is not None:
        yield '--app-name'
        yield args.app_name

    if args.icon is not None:
        yield '--icon'
        yield args.icon

    if args.category is not None:
        yield '--category'
        yield args.category

    if args.hint is not None:
        yield '--hint'
        yield args.hint

    if args.version:    # Boolean switch.
        yield '--version'

    yield args.summary

    if args.body is not None:
        yield args.body
