#! /usr/bin/env python3

from distutils.core import setup


setup(
    name='usernotify',
    version='latest',
    author='Richard Neumann',
    maintainer='Richard Neumann',
    py_modules=['usernotify'],
    scripts=['notify-user', 'notify-users'],
    description=('User notification bindings based on notify-send.'))
