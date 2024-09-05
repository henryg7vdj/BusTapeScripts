#!/usr/bin/python

# Script to download files attached to Bus Tapes on the ITk Production Database

import os
import getpass
from dotenv import load_dotenv

# Read access codes from .env file if it exists, if not set using getpass
load_dotenv()
if os.environ.get('ITKDB_ACCESS_CODE1') is None:
    os.environ['ITKDB_ACCESS_CODE1'] = getpass.getpass("Access code 1: ")
if os.environ.get('ITKDB_ACCESS_CODE2') is None:
    os.environ['ITKDB_ACCESS_CODE2'] = getpass.getpass("Access code 2: ")
import itkdb
import sys

TapeList = []

if len(sys.argv)>1:
    if os.path.isfile(sys.argv[1]):	# if argument is file, read lines and add to TapeList
        with open(sys.argv[1]) as file:
            TapeList += [line.rstrip() for line in file]
    else:
        TapeList.append(sys.argv[1])  # assume argument is tape. Add to TapeList


if __name__ == "__main__":
    
    print("Log on to ITk production database")
    client = itkdb.Client(use_eos=True)
    client.user.authenticate()

    print("Get list of registered bus tapes")
    dto_in = { u'filterMap' : { u'project':u'S',u'subproject':[u'SB'],u'componentType':[ u'BT'],u'state':['ready','requestedToDelete'] },   u'pageInfo': {u'pageIndex': 0, u'pageSize': 10000}}
    dto_out = client.get("listComponents", json = dto_in)

    for item in dto_out:
        Component = str(item['serialNumber'])
        InstitutionCode = item['institution']['code']
        Attachments = ""
        if Component in TapeList:
            dto_tape = {u'component': Component, "noEosToken" : False}
            dto_tape_out = client.get('getComponent', json = dto_tape)
            for attachment in dto_tape_out["attachments"]: 
                Attachments = attachment['filename'] + " (" + attachment['title'] + ", " + attachment['type'] +  "), "
                print("Downloading " + Component + "\t"  + Attachments)             
                if attachment['type'] == "eos":
                    download = client.get(attachment["url"])
                    download.save(attachment['title'])                
                else:
                    dto_attachment = {"component" : Component, "code" : attachment["code"]}
                    download = client.get("getComponentAttachment", json=dto_attachment)
#                    download = client.get("uu-app-binarystore/getBinaryData", json=dto_attachment)
                    download.save()

    print("Done")
