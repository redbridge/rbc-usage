#!/usr/bin/env python
# −*− coding: UTF−8 −*−
#
# Cloudusage
# collects and calculates daily totals for all cloudstack users
# Needs select privs in cloud and cloud_usage databases (the uri may thus point to the slave mysql)
# Needs a database to write the calculated daily totals to
#
import sys, os, time
import ConfigParser
import logging
import random
from datetime import datetime, timedelta
from optparse import OptionParser
from rbc_usage.common import logging_config
from rbc_usage.common.model import *
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref, clear_mappers
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, Float, String, Date, Enum, ForeignKey, func, or_

logging.basicConfig(format='%(asctime)s %(message)s')
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
config_file = 'cloudusage.cfg'
for loc in os.curdir, os.path.expanduser("~"), "/opt/redbridge/rbc-usage/etc", os.environ.get('PWD'):
    if os.path.exists(os.path.join(loc,config_file)):
        try:
            config = ConfigParser.ConfigParser()
            config.read(os.path.join(loc,config_file))
        except IOError:
            pass
# These are automap classes
class AccountCsU(object):
    ''' This is the cloud_usage account table '''
    pass

class UsageEventCsU(object):
    ''' This is the cloud_usage usage_event table '''
    pass

class CloudUsageCsU(object):
    ''' This is the cloud_usage cloud_usage table '''
    pass

class AccountCs(object):
    ''' This is the cloud account table '''
    pass

class DiskOfferingCs(object):
    ''' This is the service_offering table '''
    pass

class TemplateCs(object):
    ''' This is the  vm_template table'''
    pass

class GuestOSCs(object):
    ''' This is the guest_os table '''
    pass

def create_session():
    # cloud_usage
    engine_csu = create_engine(config.get('main', 'cloud_usage_uri'))
    metadata_csu = MetaData(engine_csu)
    account_csu = Table('account', metadata_csu, autoload=True)
    mapper(AccountCsU, account_csu)
    usage_event_csu = Table('usage_event', metadata_csu, autoload=True)
    mapper(UsageEventCsU, usage_event_csu)
    cloud_usage_csu = Table('cloud_usage', metadata_csu, autoload=True)
    mapper(CloudUsageCsU, cloud_usage_csu)
    # cloud database
    engine_cs = create_engine(config.get('main', 'cloud_uri'))
    metadata_cs = MetaData(engine_cs)
    account_cs = Table('account', metadata_cs, autoload=True)
    mapper(AccountCs, account_cs)
    disk_offering_cs = Table('disk_offering', metadata_cs, autoload=True)
    mapper(DiskOfferingCs, disk_offering_cs)
    template_cs = Table('vm_template', metadata_cs, autoload=True)
    mapper(TemplateCs, template_cs)
    guest_os_cs = Table('guest_os', metadata_cs, autoload=True)
    mapper(GuestOSCs, guest_os_cs)

    SessionCs = sessionmaker(bind=engine_cs)
    session_cs = SessionCs()
    SessionCsU = sessionmaker(bind=engine_csu)
    session_csu = SessionCsU()

    # setup our dedicated model
    engine = create_engine(config.get('main', 'rbc_usage_uri'))
    Session = sessionmaker(bind=engine)
    session = Session()
    return (session_csu, session_cs, session)

def init_db():
    engine = create_engine(config.get('main', 'rbc_usage_uri'))
    Base.metadata.create_all(engine)


def update_usage(session_cloud_usage, session_cloud, session, start=None, force = False):
    accounts = session_cloud.query(AccountCs).all()
    for account in accounts:
        try:
            usage_account = Account(account_name = account.account_name, account_uuid = account.uuid)
            session.add(usage_account)
            session.commit()
        except IntegrityError: # Trying to insert a duplicate uuid
            session.rollback()
            try:
                # Update account name
                session.query(Account).filter_by(account_uuid = account.uuid).update({'account_name': account.account_name}) # this should never fail
                session.commit()
            except Exception, e:
                print "Error updating account: %s" % e
            usage_account = session.query(Account).filter_by(account_uuid = account.uuid).one() # this should never fail
        # Now update usage for the different types
        running_vm_usage = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=1)\
                .group_by(CloudUsageCsU.offering_id).all()
        for offering in running_vm_usage:
            offering_uuid = session_cloud.query(DiskOfferingCs).filter_by(id=offering[0].offering_id).one().uuid
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(offering_uuid=offering_uuid)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='vm_running')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start)\
                        .filter_by(offering_uuid=offering_uuid)\
                        .filter_by(account=usage_account)\
                        .filter_by(usage_type='vm_running')\
                        .count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start)\
                            .filter_by(offering_uuid=offering_uuid)\
                            .filter_by(account=usage_account).one() # this entry exists
                    session.delete(usage_entry)
                    session.commit()
                usage_entry = UsageEntry(start , usage_account, 1, offering[1], offering_uuid = offering_uuid)
                session.add(usage_entry)
                session.commit()
        # Get os type usage for running vm's
        vm_guest_os_usage = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=1)\
                .group_by(CloudUsageCsU.template_id).all()
        ue = {}
        for template in vm_guest_os_usage:
            os_type = session_cloud.query(TemplateCs).filter_by(id=template[0].template_id).one().guest_os_id
            description = session_cloud.query(GuestOSCs).filter_by(id=os_type).one().display_name
            if ue.has_key(description):
                ue[description] += template[1]
            else:
                ue[description] = template[1]
        for description in ue.keys():
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(description=description)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='os_usage')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start)\
                        .filter_by(description=description)\
                        .filter_by(account=usage_account)\
                        .filter_by(usage_type='os_usage')\
                        .count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start)\
                            .filter_by(description=description)\
                            .filter_by(account=usage_account).one() # this entry exists
                    session.delete(usage_entry)
                    session.commit()
                usage_entry = UsageEntry(start , usage_account, 0, float(ue[description]), description = description)
                session.add(usage_entry)
                session.commit()

        allocated_vm_usage = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=2)\
                .group_by(CloudUsageCsU.offering_id).all()
        for offering in allocated_vm_usage:
            offering_uuid = session_cloud.query(DiskOfferingCs).filter_by(id=offering[0].offering_id).one().uuid
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(offering_uuid=offering_uuid)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='vm_allocated')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start)\
                        .filter_by(offering_uuid=offering_uuid)\
                        .filter_by(account=usage_account)\
                        .filter_by(usage_type='vm_allocated')\
                        .count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start)\
                            .filter_by(offering_uuid=offering_uuid)\
                            .filter_by(account=usage_account).one() # this entry exists
                    session.delete(usage_entry)
                    session.commit()
                usage_entry = UsageEntry(start , usage_account, 2, offering[1], offering_uuid = offering_uuid)
                session.add(usage_entry)
                session.commit()

        allocated_ip_usage = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=3)\
                .group_by(CloudUsageCsU.description).all()
        for ip in allocated_ip_usage:
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(description=ip[0].description)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='ip_address_allocated')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start)\
                        .filter_by(description=ip[0].description)\
                        .filter_by(account=usage_account)\
                        .filter_by(usage_type='ip_address_allocated')\
                        .count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start)\
                            .filter_by(description=ip[0].description)\
                            .filter_by(account=usage_account).one() # this entry exists
                    session.delete(usage_entry)
                    session.commit()
                usage_entry = UsageEntry(start , usage_account, 3, ip[1], description = ip[0].description)
                session.add(usage_entry)
                session.commit()

        network_bytes_sent = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=4).all()
        for bytes_sent in network_bytes_sent:
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='network_bytes_sent')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='network_bytes_sent').count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='network_bytes_sent').one()
                    session.delete(usage_entry)
                    session.commit()
                if bytes_sent[1]:
                    usage_entry = UsageEntry(start , usage_account, 4, bytes_sent[1])
                    session.add(usage_entry)
                    session.commit()

        primary_byte_hours = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage * CloudUsageCsU.size))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter_by(usage_type=6).all()
        for p_byte_hours in primary_byte_hours:
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='primary_byte_hours')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='primary_byte_hours').count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='primary_byte_hours').one()
                    session.delete(usage_entry)
                    session.commit()
                if p_byte_hours[1]:
                    usage_entry = UsageEntry(start , usage_account, 6, p_byte_hours[1])
                    session.add(usage_entry)
                    session.commit()

        secondary_byte_hours = session_cloud_usage.query(CloudUsageCsU, func.sum(CloudUsageCsU.raw_usage * CloudUsageCsU.size))\
                .filter_by(account_id=account.id)\
                .filter_by(start_date=start)\
                .filter(or_(CloudUsageCsU.usage_type==7, CloudUsageCsU.usage_type==8, CloudUsageCsU.usage_type==9)).all()
        for s_byte_hours in secondary_byte_hours:
            if session.query(UsageEntry).filter_by(date=start)\
                    .filter_by(account=usage_account )\
                    .filter_by(usage_type='secondary_byte_hours')\
                    .count(): # this entry exists
                pass
            else:
                if force and session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='secondary_byte_hours').count():
                    usage_entry = session.query(UsageEntry).filter_by(date=start).filter_by(account=usage_account ).filter_by(usage_type='secondary_byte_hours').one()
                    session.delete(usage_entry)
                    session.commit()
                if s_byte_hours[1]:
                    usage_entry = UsageEntry(start , usage_account, 7, s_byte_hours[1])
                    session.add(usage_entry)
                    session.commit()


def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-s', '--start', dest="start", help="Start date")
    parser.add_option('-e', '--end', dest="end", help="End date")
    parser.add_option('-f', '--force', dest="force", action="store_true", default=False, help="Force updates")
    parser.add_option('-i', '--initdb', dest="initdb", action="store_true", default=False, help="Initialize the database")
    parser.add_option('-n', '--no-splay', dest="nosplay", action="store_true", default=False, help="Disable splay")
    (options, args) = parser.parse_args()
    start = datetime.strptime(options.start, '%Y-%m-%d')
    if options.end:
        end = datetime.strptime(options.end, '%Y-%m-%d')
    else:
        end = start
    delta = end - start
    session_csu, session_cs, session = create_session()
    if options.initdb:
        init_db()
    else:
        # splay if needed, up to 3 minutes
        if not options.nosplay:
            time.sleep(random.randrange(1,180,10))
        start_time = time.time()
        for i in range(delta.days + 1):
            run_day = start + timedelta(days=i)
            update_usage(session_csu, session_cs, session, start=run_day, force=options.force)
        print "Done!. Runtime:", time.time() - start_time, "seconds"
