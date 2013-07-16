from sqlalchemy.orm import mapper, sessionmaker, relationship, backref, clear_mappers
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, Float, String, Date, Enum, ForeignKey, func, or_

Base = declarative_base()

class Account(Base):
    ''' This is the main daily usage table '''
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    account_name = Column(String(64), nullable = False)
    account_uuid = Column(String(64), nullable = False, unique = True)

class UsageEntry(Base):
    ''' This is the usage_entry table '''
    __tablename__ = 'usage_entries'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable = False)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    usage_type = Column(Enum('vm_running','vm_allocated',
                            'ip_address_allocated',
                            'network_bytes_sent', 'primary_byte_hours', 
                            'secondary_byte_hours', 'swift_byte_hours', 
                            'swift_bytes_sent'))
    offering_uuid = Column(String(128))
    description = Column(String(128))
    daily_usage = Column(Float) # This field will store byte-hours/day for primary and secondary storage, hours/offering for vm, total hours for ip addresses, and bytes sent/day for network
    account = relationship('Account', backref=
                backref('usage_entries', lazy='dynamic'))

    def __init__(self, date, account, usage_type, raw_usage, size=None, offering_uuid=None, description=None):
        if usage_type == 1: # running vm time
            self.usage_type = 'vm_running'
            self.daily_usage = raw_usage
            self.offering_uuid = offering_uuid
            self.account = account
            self.date = date
        elif usage_type == 2: # allocated vm time
            self.usage_type = 'vm_allocated'
            self.daily_usage = raw_usage
            self.offering_uuid = offering_uuid
            self.account = account
            self.date = date
        elif usage_type == 3: # ip_address_allocated
            self.usage_type = 'ip_address_allocated'
            self.daily_usage = raw_usage
            self.description = description
            self.account = account
            self.date = date
        elif usage_type == 4: # network bytes sent
            self.usage_type = 'network_bytes_sent'
            self.daily_usage = raw_usage
            self.account = account
            self.date = date
        elif usage_type == 6: # primary storage
            self.usage_type = 'primary_byte_hours'
            self.daily_usage = raw_usage
            self.account = account
            self.date = date
        elif usage_type in [7,8,9]: # secondary storage
            self.usage_type = 'secondary_byte_hours'
            self.daily_usage = raw_usage
            self.account = account
            self.date = date
        elif usage_type == 100:
            self.usage_type = 'swift_byte_hours'
            self.daily_usage = raw_usage
            self.account = account
            self.date = date
        elif usage_type == 101:
            self.usage_type = 'swift_bytes_sent'
            self.daily_usage = raw_usage
            self.account = account
            self.date = date

