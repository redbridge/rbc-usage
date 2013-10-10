#!/usr/bin/env python
# −*− coding: UTF−8 −*−
#
# swiftusage collector
import ConfigParser 
import logging
import subprocess
import os
from datetime import datetime
from rbc_usage.common.model import *
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker, scoped_session, relationship, backref, clear_mappers
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError


config_file = 'swiftusage.cfg'
for loc in os.curdir, os.path.expanduser("~"), "/opt/redbridge/rbc-usage/etc", os.environ.get('PWD'):
    if os.path.exists(os.path.join(loc,config_file)):
        try: 
            config = ConfigParser.ConfigParser()
            config.read(os.path.join(loc,config_file))
        except IOError:
            pass

def get_swift_stats(account, auth_token):
    swift_url = config.get('swift', 'swift_url')
    swift_user = config.get('swift', 'swift_admin_user')
    swift_key = config.get('swift', 'swift_admin_key')
    swift_account = config.get('swift', 'swift_admin_accountid')
    out = subprocess.Popen("swift --os-auth-token %s --os-storage-url %s/v1/%s stat" % (auth_token, swift_url, account), shell=True, stdout=subprocess.PIPE)
    for line in out.stdout:
        if "Bytes: " in line:
            return line.split(':')[1].strip()
    return False

def get_swift_auth_token():
    swift_url = config.get('swift', 'swift_url')
    swift_user = config.get('swift', 'swift_admin_user')
    swift_key = config.get('swift', 'swift_admin_key')
    swift_account = config.get('swift', 'swift_admin_accountid')
    out = subprocess.Popen("curl -k -s -H 'X-Auth-User: %s:%s' -H 'X-Auth-Key: %s' %s/auth/v1.0 -I" % (swift_account, swift_user, swift_key, swift_url), shell=True, stdout=subprocess.PIPE)
    for line in out.stdout:
        if "X-Auth-Token" in line:
            return line.split(':')[1].strip()
    return False

def account_stats(session):
    # first get a list of accounts in CS
    accounts = session.query(Account).all()
    # loop thru the accounts and get stats for the account
    swift_token = get_swift_auth_token()
    start = datetime.now()
    for account in accounts:
        account_bytes = get_swift_stats(account.account_name, swift_token)
        if account_bytes:
            if session.query(UsageEntry).filter_by(date=start.strftime('%Y-%m-%d'))\
                    .filter_by(account=account )\
                    .filter_by(usage_type='swift_byte_hours')\
                    .count(): # this entry exists
                # update entry
                ue = UsageEntry.query.filter_by(date=start.strftime('%Y-%m-%d'))\
                        .filter_by(account=account )\
                        .filter_by(usage_type='swift_byte_hours')\
                        .first()
                checkins = ue.description.split(':')
                if not str(datetime.now().hour) in checkins:
                    ue.daily_usage += float(account_bytes)
                    ue.description = "%s:%s" % (ue.description,datetime.now().hour)
                    session.add(ue)
                    session.commit()
            else:
                usage_entry = UsageEntry(start.strftime('%Y-%m-%d') , account, 100, account_bytes, description=datetime.now().hour)
                session.add(usage_entry)
                session.commit()


def main():
    engine = create_engine(config.get('main', 'rbc_usage_uri')) 
    db_session = scoped_session(sessionmaker(bind=engine))
    Base.query = db_session.query_property()
    account_stats(db_session)

if __name__ == '__main__':
    main()
