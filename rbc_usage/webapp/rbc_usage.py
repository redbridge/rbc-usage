#!/usr/bin/env python
# −*− coding: UTF−8 −*−
import logging
import json
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask import request, jsonify, abort
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine, MetaData, Table
from model import *

app = Flask(__name__)
app.config.from_object('rbc_usage.webapp.default_settings.DevelopmentConfig')
app.config.from_envvar('RBC_USAGE')

engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
Base.query = db_session.query_property()

@app.errorhandler(404)
def api_not_found(mess):
    return jsonify({'responseType': 'errorResponse', 'message': 'Not found' })

@app.errorhandler(401)
def api_unauthorized(mess):
    return jsonify({'responseType': 'errorResponse', 'message': 'Unauthorized' })

@app.errorhandler(400)
def api_bad_request(mess):
    print mess
    return jsonify({'responseType': 'errorResponse', 'message': 'Bad request' })

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.route('/usage/<account_uuid>', methods=['GET'])
def usage(account_uuid):
    try:
        account = db_session.query(Account).filter(Account.account_uuid==account_uuid).one()
    except:
        abort(400)
    if request.args.get('start'):
        try:
            start = datetime.strptime(request.args.get('start'), '%Y-%m-%d')
        except:
            abort(400)
    else:
        start = datetime.now() - timedelta(1)
    if not request.args.get('end'):
        end = start
    else:
        try:
            end = datetime.strptime(request.args.get('end'), '%Y-%m-%d')
        except:
            abort(400)
    try:
        usage_entries_os_usage = db_session.query(UsageEntry.description, func.sum(UsageEntry.daily_usage))\
                .filter(UsageEntry.account == account)\
                .filter(UsageEntry.date.between(start,end))\
                .filter(UsageEntry.usage_type=='os_usage')\
                .group_by(UsageEntry.description).all()
        usage_entries_vm_running = db_session.query(UsageEntry.offering_uuid, func.sum(UsageEntry.daily_usage))\
                .filter(UsageEntry.account == account)\
                .filter(UsageEntry.date.between(start,end))\
                .filter(UsageEntry.usage_type=='vm_running')\
                .group_by(UsageEntry.offering_uuid).all()
        usage_entries_vm_allocated = db_session.query(UsageEntry.offering_uuid, func.sum(UsageEntry.daily_usage))\
                .filter(UsageEntry.account == account)\
                .filter(UsageEntry.date.between(start,end))\
                .filter(UsageEntry.usage_type=='vm_allocated')\
                .group_by(UsageEntry.offering_uuid).all()
        usage_entries_ip_allocated = db_session.query(UsageEntry.description, func.sum(UsageEntry.daily_usage))\
                .filter(UsageEntry.account == account)\
                .filter(UsageEntry.date.between(start,end))\
                .filter(UsageEntry.usage_type=='ip_address_allocated')\
                .group_by(UsageEntry.description).all()
        usage_entries = db_session.query(UsageEntry.usage_type, func.sum(UsageEntry.daily_usage))\
                .filter(UsageEntry.account == account)\
                .filter(UsageEntry.date.between(start,end))\
                .filter(UsageEntry.usage_type!='os_usage')\
                .filter(UsageEntry.usage_type!='vm_running')\
                .filter(UsageEntry.usage_type!='vm_allocated')\
                .filter(UsageEntry.usage_type!='ip_address_allocated')\
                .group_by(UsageEntry.usage_type).all()
    except:
        abort(400)
    return jsonify({
        'responseType': 'usageResponse',
        'start': start.strftime('%Y-%m-%d'),
        'end': end.strftime('%Y-%m-%d'),
        'os_usage': dict(usage_entries_os_usage),
        'vm_running': dict(usage_entries_vm_running),
        'vm_allocated': dict(usage_entries_vm_allocated),
        'ip_address_allocated': dict(usage_entries_ip_allocated),
        'usage': dict(usage_entries)
        })

if __name__ == '__main__':
    handler = RotatingFileHandler('rbc_usage.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run()
