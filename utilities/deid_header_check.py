#!/usr/bin/env python

import argparse
import flywheel
import os
import pandas as pd
import pydicom
import re

def add_first_acquisition_header_info(sub_id, sub_label, ses, patient_identifier_keys, data_dict):

    test_acq = None
    # This is the dicom archive file we will extract a dcm file from
    test_file = None
    # Find the first acquisition that has a dicom zip file
    # ignore Phoenix zip files
    for acq in ses.acquisitions.iter():
        if acq.label.lower().startswith('phoenix'):
            continue
        for f in acq.files:
            if (f.type == 'dicom'):
                # Should be able to use f.zip_member_count, but this sometimes None
                # even when the zip file is not empty
                if (f.name.lower().endswith('.zip')) and f.size > 512:
                    test_acq = acq
                    test_file = f
                    break

    if test_acq is None:
        data_dict['subject_id'].append(sub_id)
        data_dict['subject_label'].append(sub_label)
        data_dict['session_id'].append(ses_id)
        data_dict['session_label'].append(ses_label)
        data_dict['acquisition_id'].append(pd.NA)
        data_dict['acquisition_label'].append(pd.NA)
        data_dict['file_name'].append(pd.NA)
        data_dict['file_user'].append(pd.NA)
        data_dict['file_created'].append(pd.NA)
        data_dict['header_deidentification_method'].append(pd.NA)
        data_dict['header_has_patient_identifiers'].append(pd.NA)
        data_dict['header_patient_identifiers_populated'].append(pd.NA)
        return

    acq_label = test_acq.label
    acq_id = test_acq.id

    file_name = test_file.name
    file_user = test_file.origin['id']
    file_created = str(test_file.created.date())

    # deid_method from the header, not metadata
    dcm_deid_method = pd.NA
    dcm_has_patient_identifiers = False
    dcm_patient_identifiers_populated = False

    # The actual dcm file (might not have .dcm extension in the zip)
    # This is extracted from test_file and written to disk
    tmp_dcm_file = 'deid_header_check_data.dcm'

    if os.path.exists(tmp_dcm_file):
        os.remove(tmp_dcm_file)

    # Download the first file in the zip archive
    fw_dcm = test_file.get_zip_info().members[0]
    test_file.download_zip_member(fw_dcm.path, tmp_dcm_file)

    # try to read the file, but catch exception
    try:
        dcm = pydicom.dcmread(tmp_dcm_file)

        if ('DeidentificationMethod' in dcm):
            dcm_deid_method = dcm['DeidentificationMethod'].value

        identifier_keys = [id_key for id_key in patient_identifier_keys if id_key in dcm]

        for key in identifier_keys:
            # Need to enumerate data element here and check if empty
            element = dcm.data_element(key)
            if not element.is_empty:
                dcm_has_patient_identifiers = True
                # Check for alphanumeric characters
                if any(char.isalnum() for char in str(element.value)):
                    dcm_patient_identifiers_populated = True
    except pydicom.errors.InvalidDicomError:
        print(f"Cannot read dicom from {sub_label}/{ses_label}/{acq_label}/{file_name}")
        dcm_deid_method = 'InvalidDicomError'
        dcm_has_patient_identifiers = 'InvalidDicomError'
        dcm_patient_identifiers_populated = 'InvalidDicomError'

    os.remove(tmp_dcm_file)

    data_dict['subject_id'].append(sub_id)
    data_dict['subject_label'].append(sub_label)
    data_dict['session_id'].append(ses_id)
    data_dict['session_label'].append(ses_label)
    data_dict['acquisition_id'].append(acq_id)
    data_dict['acquisition_label'].append(acq_label)
    data_dict['file_name'].append(file_name)
    data_dict['file_user'].append(file_user)
    data_dict['file_created'].append(file_created)
    data_dict['header_deidentification_method'].append(dcm_deid_method)
    data_dict['header_has_patient_identifiers'].append(dcm_has_patient_identifiers)
    data_dict['header_patient_identifiers_populated'].append(dcm_patient_identifiers_populated)


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 prog="deid_header_check", add_help=False, description='''
Script to check Flywheel DICOM file / archive *contents* for de-identification method and common
patient identifiers.

Output is a CSV file containing results for every DICOM file or DICOM zip archive in the project.
The output file is named group_project_dicom_header_deid_report.csv.

By default, the script iterates over all files in a project, it can take some time to retrieve each
file's data from the server. It can optionally take a list of session IDs.

What this script does:
     * Iterates over every subject, session or a selected list of sessions
     * Find the first acquisition with a dicom zip file (ignoring PhoenixZipReport)
     * Downloads the first dicom file from the zip and check its header
     * Report if identifiers are found

The dicom files are stored in the current working directory - they will be deleted but the user may
have to manually remove them if the script is interrupted.

The output contains information about the subject, session, acquisition, and file (meaning the dicom
zip archive). The "file_created" field refers to the date the file was uploaded to Flywheel.

The header_ fields pertain to the header of the first DICOM file in the zip archive. This is
distinct from the file's metadata (which can be checked with deid_check.py).

What this script does not do:

    * Check non-DICOM files (eg, NIFTI). Usually these will inherit identifiers from DICOM files.
      While NIFTI files generally do not contain identifiers, it is possible that subject IDs could
      be encoded in the description field.

    * Check all possible identifiers. The script checks a selection of direct identifiers including
      PatientName, PatientID, PatientAddress, and PatientBirthDate.

    * Validate the de-identification. The script outputs the reported deidentification method, but
      does not check that the de-identification actually happened to the specification of that
      method, beyond checking the selected direct identifiers.

    * Check metadata above the file level, for example it does not check if the Subject container
      contains PII. Often these will only be populated through DICOM import.

    * Check any private tags.

''')
required = parser.add_argument_group('Required arguments')
required.add_argument("group", help="Group label", type=str)
required.add_argument("project", help="Project label", type=str)

optional = parser.add_argument_group('Optional arguments')
optional.add_argument("-h", "--help", action="help", help="show this help message and exit")
optional.add_argument("-s", "--sessions", help="Text file containing a list of session IDs, one per line. " \
                      "Use this to check a subset of sessions in the project.", type=str, default = None)

args = parser.parse_args()

fw = flywheel.Client()

# First generate our "data dictionary" that will contain the values we want to track
data_dict = {'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[],
             'acquisition_id':[], 'acquisition_label':[], 'file_name':[],'file_user':[],
             'file_created':[], 'header_deidentification_method':[],
             'header_has_patient_identifiers':[], 'header_patient_identifiers_populated':[]}

# List of patient direct identifiers to check. If ANY of these exist for a file,
# then set file_has_patient_identifiers = True
#
# Having identifiers is usually bad, however some studies use coded subject identifiers
# in patient info fields. The presence of identifiers without a deidentification method indicates
# serious trouble
#
patient_identifier_keys = ['AdditionalPatientHistory', 'CurrentPatientLocation', 'OtherPatientIDs',
                           'OtherPatientIDsSequence', 'OtherPatientNames', 'PatientAddress',
                           'PatientAlternativeCalendar', 'PatientBirthDate', 'PatientBirthDateInAlternativeCalendar',
                           'PatientBirthName', 'PatientBirthTime', 'PatientDeathDateInAlternativeCalendar', 'PatientID',
                           'PatientMotherBirthName', 'PatientName', 'PatientTelecomInformation', 'PatientTelephoneNumbers']

group_label = args.group
project_label = args.project
sessions_fn = args.sessions

# Get the project
project = fw.lookup(f"{group_label}/{project_label}")

if sessions_fn is not None:
    with open(sessions_fn, 'r') as sessions_io:
        session_ids = [ ses_id.rstrip() for ses_id in sessions_io.readlines()]
    for ses_id in session_ids:
        try:
            ses = fw.get(ses_id)
            sub = ses.subject
            sub_label = sub.label
            sub_id = sub.id
            ses_label = ses.label
            add_first_acquisition_header_info(sub_id, sub_label, ses, patient_identifier_keys, data_dict)
        except flywheel.ApiException as e:
            print(f"Cannot get session {ses_id}: {e}")
            continue
else:
    # Get the subjects in the project as an iterator so they don't need to be returned
    # All at once - this saves time upfront.
    subjects = project.subjects.iter()

    # Loop over the subjects
    for sub in subjects:
        # Get the subject label for our data_dict
        sub_label = sub.label
        sub_id = sub.id
        # Get this subject's sessions as an iterator and loop through them
        sessions = sub.sessions.iter()
        for ses in sessions:
            # Get the session's label for our data_dict
            ses_label = ses.label
            ses_id = ses.id
            add_first_acquisition_header_info(sub_id, sub_label, ses, patient_identifier_keys, data_dict)

# Convert the dict to a pandas dataframe
df = pd.DataFrame.from_dict(data_dict)

# write file

filename = f"{group_label}_{project_label}_dicom_zip_header_deid_report.csv"
df.to_csv(filename,index=False, na_rep = 'NA')
