#!/usr/bin/python3

from setuptools import setup

# read the contents of your README file
from os import path
with open(path.join(path.abspath(path.dirname(__file__)), 'README.md'),
          encoding='utf-8') as f:
  description = f.read()

setup(name='polyp',
      description='A renderer that creates gdsII files from an '
                  'all-ascii human-readble layout language ',
      long_description=description,
      long_description_content_type='text/markdown',
      author='zaphB',
      version='1.0.1',
      packages=['polyp'],
      entry_points={
        'console_scripts': [
          'polyp = polyp.__main__:main'
        ],
        'gui_scripts': []
      },
      install_requires=['numpy', 'gdspy', 'matplotlib']
)
