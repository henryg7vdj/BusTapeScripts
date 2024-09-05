#!/usr/bin/python

# Script to register Bus Tapes on the ITk Production Database
# New version to upload files to EoS.  3 September 2024.

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
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime

# Set directory containing zip files to upload (from command line or default) and institution code
if len(sys.argv)>1:
    INPUT_DIR = sys.argv[1];
else:
    INPUT_DIR = r"/home/henry/programs/python/DB2024/TestX"
InstitutionCode = 'OX'

def create_json_from_zip(zipfile):
    typeNo = 0  # 1 (Left Long), 2 (Right Long), 3 (Left Short), 4 (Right Short), anything else = undefined
    typeName = 'LEFT_LONG' # default setting for undefined tapes
    with ZipFile(zipfile, 'r') as z:
        data = z.read('Measurement Report.txt')
        datasplit = data.splitlines()
        for part in datasplit:
            part = part.decode('utf-8')  # removes b which python 3 sticks at front of strings
            if(part.find('Measurement report') >=0):
                fileDescription=part
            if(part.find('Design') >=0):
                design=part
                if 'LHS' in design and 'LS' in design:
                    typeNo =1
                    typeName = 'LEFT_LONG'
                if 'RHS' in design and 'LS' in design:
                    typeNo =2
                    typeName = 'RIGHT_LONG'
                if 'LHS' in design and 'SS' in design:
                    typeNo =3
                    typeName = 'LEFT_SHORT'
                if 'RHS' in design and 'SS' in design:
                    typeNo =4
                    typeName = 'RIGHT_SHORT'
            if(part.find('Manufacturer') >=0):
                manufacturer = part
            if (part.find('Serial') >= 0):
                serNo = part.split()[2]
                ATLASserNo = '20USBBT' + str(typeNo) + '%06d' % int(serNo)
    newjson = {u'attachments': [{u'title': zipfile.split("/")[-1], u'description': fileDescription, u'type':u'file', u'filename': zipfile}],
               u'dtoIn': {u'componentType': u'BT', # u'comments': [design, manufacturer],
                           u'project': u'S', u'subproject': u'SB',
                          u'properties' : { u'DESIGN':design[9:] , u'MANUFACTURER':manufacturer[15:]},
                          u'serialNumber': ATLASserNo , u'type': typeName, u'institution': InstitutionCode}}
    return newjson

if __name__ == "__main__":
    print("*** Tape Test Data Uploader ***")
    client = itkdb.Client(use_eos=True)
    client.user.authenticate()
    print("Process files in directory: " + INPUT_DIR)
    input_dir = Path(INPUT_DIR)
    if input_dir.is_dir():
        array_json = [x for x in os.listdir(INPUT_DIR) if x.endswith(".zip")] # create list of files in directory
        for file in array_json: # Loop through all input files in directory
            print("Process: " + file)
            print("Unzip file and read ID number")
            # Will need this dto to set test runs later
            dto_test_metrology = {"testType": "BTMETROLOGY",
                        "institution": InstitutionCode,
                        "runNumber": "",
                        }
            dto_test_electrical = {"testType": "BTELECTRICAL",
                        "institution": InstitutionCode,
                        "runNumber": "",
                        }
            with ZipFile(INPUT_DIR + "/" + file, 'r') as z: # open zip file, read serial no and stage
                data = z.read('Measurement Report.txt')
                datasplit = data.splitlines()
                for part in datasplit:
                    part = part.decode('utf-8')  # removes b which python 3 sticks at front of strings
                    if (part.find("Serial") >= 0):
                        serNo = part.split()[2]
                    if (part.find("Production Stage") >=0):
                        stage = part.split()[3]
                    if (part.find("Measurement report") >= 0):
                        datestamp = datetime.strptime(part[31:],
                                                      '%d %B %Y %H:%M:%S')  # put date in format required by database,  or it will refuse dto
                        dto_test_metrology["date"] = datestamp.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        dto_test_electrical["date"] = datestamp.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        print("Test date: " + datestamp.strftime('%d.%m.%Y'))
                    if (part.find('Production Stage') >= 0):
                        dto_test_metrology["runNumber"] = part.split()[3]
                        dto_test_electrical["runNumber"] = part.split()[3]

                # Read PASS or FAIL from header of htm file and read test results
                stretchValue = 0.0
                nSV = 0
                max_dy = 0.0
                nMDY = 0
                nShortsOrHV = 0
                nRed = 0
                nAmber = 0
                print("Read report.html")
                data = z.read("report.htm")
                datasplit = data.splitlines()
                dto_test_electrical["passed"] = False  # default is fail unless pass message found
                dto_test_metrology["passed"] = False  # default is fail unless pass message found
                dto_test_metrology["problems"] = False
                for part in datasplit:
                    part = part.decode('utf-8')  # removes b which python 3 sticks at front of strings
                    if (part.find('Tape has PASSED stretch test') >= 0):
                        dto_test_metrology["passed"] = True
                    if (part.find('Stretch dx/x') >= 0):
                        vs = part.split()[2]
                        vs = vs.split('<')[0] # deal with -0.000248<br
                        stretchValue += abs(float(vs))
                        nSV += 1
                    if (part.find('Max dy') >= 0):
                        vs = part.split()[2]
                        vs = vs.split('<')[0]  # deal with -0.000248<br
                        max_dy += abs(float(vs))
                        nMDY += 1
                    if (part.find('Tape has PASSED the test') >= 0):
                        dto_test_electrical["passed"] = True
                        print ("Test result: PASSED")
                    if (part.find('nets flagged with shorts or HV failure') >= 0):
                        nShortsOrHV = abs(int(part.split()[0]))
                    if (part.find('nets flagged RED in TapeTestLog') >= 0):
                        nRed = abs(int(part.split()[0]))
                    if (part.find('nets flagged AMBER in TapeTestLog') >= 0):
                        nAmber = abs(int(part.split()[0]))
                testresults = {"DXVSX": -1, "MAXDY": -1}
                if (nSV > 0):
                    stretchValue = stretchValue / float(nSV)
                    testresults["DXVSX"] = stretchValue
                if (nMDY > 0):
                    max_dy = max_dy / float(nMDY)
                    testresults["MAXDY"] = max_dy
                dto_test_metrology["results"] = testresults
                testproperties = {"FILE": file}
                dto_test_metrology["properties"] = testproperties
                testresults = {"SHORTS_OR_HV_FAILURE": nShortsOrHV, "RED_FLAGS": nRed,
                               "AMBER_FLAGS": nAmber}
                dto_test_electrical["results"] = testresults
                testproperties = {"FILE": file}
                dto_test_electrical["properties"] = testproperties

            # Get list of all bus tapes on database
            dto_in = { u'filterMap' : { u'project':u'S',u'subproject':[u'SB'],u'componentType':[ u'BT']},
                      u'pageInfo': {u'pageIndex': 0, u'pageSize': 10000}}
            dto_out = client.get("listComponents", json = dto_in)
            json_file_data = create_json_from_zip(INPUT_DIR + "/" + file) # make json from input (zip) file
            print("Check if " + json_file_data['dtoIn']['serialNumber'] + " is on database.")
            dto_test_metrology["component"] = json_file_data['dtoIn']['serialNumber']
            dto_test_electrical["component"] = json_file_data['dtoIn']['serialNumber']
            component_code = None
            if (dto_out): # look if a tape on the database has the serial no of input tape
                for item in dto_out:
                    if 'serialNumber' in item:
                        itemNo = item['serialNumber']
                        if (itemNo == json_file_data['dtoIn']['serialNumber']):
                            component_code = itemNo # this is ATLAS serial number
                            print("Found: "+component_code)
            if component_code is not None:
                newComponent=False
                # Found bus tape on database
                # Check if zip file already uploaded
                dto_tape = {u'component': component_code}
                dto_tape_out = client.get('getComponent', json = dto_tape)
                if dto_tape_out:
                    for attachment in dto_tape_out["attachments"]: # check if file with matching filename and
                        # timestamp is already uploaded. If so delete existing one before uploading new.
                        for newattachment in json_file_data["attachments"]:
                            if    (attachment["description"] == newattachment["description"]):
                                print("File already uploaded: " + attachment["filename"] + ". " +
                                                                            attachment["description"] + ". Delete it.")
                                deleteAttachmentDto = { 'component': component_code, 'code' : attachment['code'] }
                                client.post("deleteComponentAttachment" , json = deleteAttachmentDto)
            else:
                newComponent=True
                print ("Component not found")
                print ("Register component")
                response_json = client.post('registerComponent', json = json_file_data['dtoIn'])
                component_code = response_json["component"]["serialNumber"]
                print ("Registered "+component_code)
            print ("Upload zip file")
            if json_file_data["attachments"] is not None:
                for attachment in json_file_data["attachments"]:
                    data ={ 'component': component_code,
                            'title': attachment["title"],   
                            'description': attachment["description"],
                            'url' : attachment["filename"],
                            'type': attachment["type"] } 
                    with open(attachment["filename"], "rb") as fpointer:
                        attached = { "data" : itkdb.utils.get_file_components({"data" : fpointer})}
                        client.post('createComponentAttachment' , data = data, files=attached)
            if stage == 'Bare': # from zip
                stageCode = 'BARE'
            elif stage == 'Stave':
                stageCode = 'COMPLETED'
            else:
                stageCode = 'COCURED'
            prevStage = stageCode
            if (not newComponent): # if updating existing DB entry
                prevStage = dto_tape_out["currentStage"]["code"]
            if(prevStage=='COMPLETED' or (prevStage=='COCURED' and stageCode!='COMPLETED') or prevStage==stageCode):
                # do not change stage if already at a later stage as we are presumably re-uploading an old file
                print( 'Stage on database: ' + prevStage + '. This file: '+ stageCode + '. Do not change.')
            else:
                print ("Set stage to " + stage + " (" + stageCode + ")")
                stage_json = {u'component': component_code, u'stage': stageCode}
                client.post('setComponentStage', json = stage_json)
            # Set Test Results
            # Search for associated tests
            testlist = ['BTMETROLOGY', 'BTELECTRICAL']
            testdto = {'BTMETROLOGY': dto_test_metrology, 'BTELECTRICAL' : dto_test_electrical}
            for testname in testlist:
                print("Search for existing tests matching " + file + "  " + testdto[testname]["date"])
                dto_test_search_in = {u'filterMap': {u'testType': testname,
                                                     u'serialNumber': str(component_code),
                                      u'state': ['ready', 'requestedToDelete']},
                                      u'pageInfo': {u'pageIndex': 0, u'pageSize': 10000}}
                dto_test_search_out_json = client.get('listTestRunsByComponent', json = dto_test_search_in)
                atest_filename = 'none'
                atest_date = 'none'
                if(dto_test_search_out_json):
                    for atest in dto_test_search_out_json:
                        testid = atest["id"]
                        dto_atest_in = {u'testRun': testid}
                        dto_atest_out_json = client.get('getTestRun', json = dto_atest_in)
                        if (dto_atest_out_json):
                            atest_filename = dto_atest_out_json["properties"][0]["value"]
                            atest_date = dto_atest_out_json["date"]
                        if( atest_filename == file and atest_date == testdto[testname]["date"]
                                and dto_atest_out_json["state"] != "deleted"):
                            print("Found " + testname + " test for " + atest_filename + ", " + atest_date + " Delete it.")
                            client.post('deleteTestRun', json = dto_atest_in)
                print ("Set "+testname+" test results.")
                client.post('uploadTestRunResults', json = testdto[testname])
            print ("All test results set.")
    print ("Processed all files.")

