#!/usr/bin/env python
# −*− coding: UTF−8 −*−
class Config(object):
    DEBUG = False
    TESTING = False
    DATABASE_URI = 'mysql://rbc-usage:rbc-usage@192.168.56.10/rbcusage'

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql://user@localhost/foo'

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
