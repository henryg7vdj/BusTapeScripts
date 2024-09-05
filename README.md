# BusTapeScripts

Repository for scripts to upload and download bus tape test data from the [ITk production database](https://itkpd-test.unicorncollege.cz).

These scripts use the [itkdb](https://itkdb.docs.cern.ch/) module. This can be installed by

`pip install itkdb`

To avoid entering your access codes each time, create a `.env` file in the same directory with these lines:


    ITKDB_ACCESS_CODE1=####
    ITKDB_ACCESS_CODE2=########


To upload the tape test data, copy the test zip files to a directory and run the upload script with:

`python tapeUploader.py DIRECTORY_NAME`

You can set a default input directory on line 27 of tapeUploader.py. This script will read the zip file and check if the tape is on the database. If not, it registers it. It then uploads the zip file and sets the metrology and electrical test runs. If this file has already been uploaded (identified by the timestamp) it will delete it and upload the new file, and delete and reset the test runs. If the stage has changed, it will set this.

Notes:

This is set for Oxford tapes. To use at other places, change the institution code on line 28. If the location of the tape is different, it will create an error, so make sure shipping information is up to date before uploading new test data.

Make sure all test results done at one stage are uploaded before uploading those for the next stage, otherwise the stage for the test will be set incorrectly. Although as the test Run Number is set to the stage given in the zip file, this will be recorded.

To download the attached files for a single tape type:

`python tapeDownloader.py TAPE_CODE`

where TAPE_CODE is the ATLAS serial number of the bus tape (for example 20USBBT1001602). To download the files for multiple tapes, create a text file where each line is a tape serial number and type:

`python tapeDownloader.py LIST_FILE_NAME`
