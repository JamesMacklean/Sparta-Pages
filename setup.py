# -*- coding: utf-8 -*-
#
# Imports ###########################################################

import os
from setuptools import setup

# Main ##############################################################

setup(
    name='sparta-pages',
    version='1.0',
    description='LMS - Coursebank Sparta Pages',
    packages=['sparta_pages'],
    install_requires=[
        'Django',
    ],
)
