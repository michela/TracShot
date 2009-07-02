from setuptools import setup

PACKAGE = 'TracShot'
VERSION = '0.2.4'
SUMMARY = 'Shot issue tracking for film/TV post production'
AUTHOR = 'Michela Ledwidge'
HOME_PAGE = 'http://michela.thequality.com'
AUTHOR_EMAIL = 'michela@modfilms.com'
LICENSE = ''
PLATFORM = 'any'
DESCRIPTION = ''


setup(name=PACKAGE,
      version=VERSION,
      packages=['shot'],
      entry_points={'trac.plugins': '%s = shot' % PACKAGE},
      package_data={'shot': ['templates/*.html']},
      author = AUTHOR,
      home_page = HOME_PAGE,
      author_email = AUTHOR_EMAIL,
      license = LICENSE,
      description = DESCRIPTION
)
