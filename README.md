rbc-ucage
==============================

This package provides usage services for the RBC.

Components
------------------------------
* rbc-import-cloudusage: a simple command that extracts data from the Cloudstack usage database and updates/inserts daily usage data.
    it is configured thru a config file, cloudusage.cfg, that specifies database connections. The config file should be in the CWD or in /opt/redbridge/rbc-usage/etc. 
    
    It's invoked using command line arguments:
    -s (--start ) 2012-12-12 - start date for import
    -e (--end) 2013-06-14 - end date for import
    -f (--force) - will when specified overwrite any previous dailay usage records
    -i (--initdb) - will initialize the database

    A typical cron based run would be:
        rbc-import-cloudusage -s $(date +%Y-%m-%d) -e $(date +%Y-%m-%d) 


* rbc-usage-server: A simple flask based web service, supplying usage data from requests.
    The usage server is started thru the command wrapper: rbc-usage-server, change port or bind settings in the rbc-usage-server script.
    The usage server should be protected usaing basic auth and ssl.
    It should also be run using some kind of init.d or supervisor
    A typical request for usage data is http://127.0.0.1:8888/usage/<cs account uuid>?start=2013-06-01&end=2013-06-05

    The response is json, where:
        *_byte_hours = byte_hours used (to calculate GB-hours: 337407196004352.0/1073741824/720 = 436)
        vm_allocated and running contains a list with offering uuids and used vm time for each.

example response:
{
  "end": "2013-04-30", 
  "responeType": "usageResponse", 
  "start": "2013-04-01", 
  "usage": [
    [
      "network_bytes_sent", 
      26679959392.0
    ], 
    [
      "primary_byte_hours", 
      337407196004352.0
    ], 
    [
      "secondary_byte_hours", 
      147525959417856.0
    ]
  ], 
  "vm_allocated": [
    [
      "0ecbc669-c557-4301-b121-ab54437a4839", 
      3153.552505493164
    ], 
    [
      "1f7bd1ff-b79f-4722-a151-83be524008be", 
      3600.0
    ], 
    [
      "31adcf09-e383-4f1d-8f9d-e720e538daaa", 
      2160.0
    ], 
    [
      "4ad08b0d-2e0f-4823-8e0c-ceff83768ad8", 
      8095.731399536133
    ]
  ], 
  "vm_running": [
    [
      "0ecbc669-c557-4301-b121-ab54437a4839", 
      2292.1111068725586
    ], 
    [
      "1f7bd1ff-b79f-4722-a151-83be524008be", 
      2043.3161125183105
    ], 
    [
      "31adcf09-e383-4f1d-8f9d-e720e538daaa", 
      2722.922218322754
    ], 
    [
      "4ad08b0d-2e0f-4823-8e0c-ceff83768ad8", 
      6454.786956787109
    ]
  ]
}
