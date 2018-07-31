#! /usr/bin/env python3

from distutils.core import setup
from subprocess import check_output


setup(
    name='usernotify',
    version=check_output(('git', 'rev-parse', '--short', 'HEAD')).decode(),
    author='Richard Neumann',
    maintainer='Richard Neumann',
    py_modules=['usernotify'],
    scripts=['notify-user', 'notify-users'],
    description=('User notification bindings based on notify-send.'))
