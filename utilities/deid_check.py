#!/usr/bin/env python

import argparse
import flywheel
import pandas as pd
import re

def add_acquisition_file_info(sub_id, sub_label, ses_id, ses_label, acq, file_type, patient_identifier_keys, data_dict):
    acq_label = acq.label
    acq_id = acq.id
    for f in acq.files:
        if file_type != 'all' and f.type != file_type:
            continue
        f = f.reload()
        file_name = f.name
        file_user = f.origin['id']
        file_created = str(f.created.date())
        file_info = f.info
        file_deid_method = pd.NA
        file_has_patient_identifiers = False
        file_patient_identifiers_populated = False
        file_has_info = True
        if (file_info):
            if ('DeidentificationMethod' in file_info):
                file_deid_method = file_info['DeidentificationMethod']
            identifier_keys = [id_key for id_key in patient_identifier_keys if id_key in file_info]
            for key in identifier_keys:
                value_string = str(file_info[key])
                if len(value_string) > 0:
                    file_has_patient_identifiers = True
                    # Check if file_info[key] contains alphanumeric characters
                    if any(char.isalnum() for char in value_string):
                        file_patient_identifiers_populated = True
        else:
            # This happens if the file has not had any classifiers run on it
            file_has_info = False

        data_dict['subject_id'].append(sub_id)
        data_dict['subject_label'].append(sub_label)
        data_dict['session_id'].append(ses_id)
        data_dict['session_label'].append(ses_label)
        data_dict['acquisition_id'].append(acq_id)
        data_dict['acquisition_label'].append(acq_label)
        data_dict['file_name'].append(file_name)
        data_dict['file_user'].append(file_user)
        data_dict['file_created'].append(file_created)
        data_dict['file_has_info'].append(file_has_info)
        data_dict['file_deidentification_method'].append(file_deid_method)
        data_dict['file_has_patient_identifiers'].append(file_has_patient_identifiers)
        data_dict['file_patient_identifiers_populated'].append(file_patient_identifiers_populated)


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 prog="deid_check", add_help=False, description='''
Script to check Flywheel DICOM file / archive metadata for de-identification method and common
patient identifiers.

Output is a CSV file containing results for every DICOM file or DICOM zip archive in the project.
The output file is named group_project_dicom_deid_report.csv.

Because this iterates over all files in a project, it can take some time to retrieve each file's
data from the server (based on initial tests, the script processes about 5 files / second).

What this script does:
     * Iterates over every subject, session, acquisition, file container.
     * If file is DICOM, check its metadata for the existence of common direct identifiers in
       standard DICOM fields, and also check if a deidentification method is recorded.

What this script does not do:
    * Check the DICOM files themselves. We trust that Flywheel's classification will capture
      identifiers if present, and place them in the file container.

    * Check non-DICOM files (eg, NIFTI). Usually these will inherit identifiers from DICOM files.

    * Check all possible identifiers. The script checks a selection of direct identifiers including
      PatientName, PatientID, PatientAddress, and PatientBirthDate.

    * Validate the de-identification. The script outputs the reported deidentification method, but
      does not check that the de-identification actually happened to the specification of that
      method.

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
optional.add_argument("-t", "--file-type", help="File type to check, or 'all' to check all types", type=str, default="dicom")

args = parser.parse_args()

fw = flywheel.Client()

# First generate our "data dictionary" that will contain the values we want to track
data_dict = {'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[],
             'acquisition_id':[], 'acquisition_label':[], 'file_name':[],'file_user':[],
             'file_created':[], 'file_has_info':[], 'file_deidentification_method':[],
             'file_has_patient_identifiers':[], 'file_patient_identifiers_populated':[]}

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
        ses = fw.get(ses_id)
        sub = ses.subject
        sub_label = sub.label
        sub_id = sub.id
        ses_label = ses.label
        acquisitions = ses.acquisitions.iter()
        for acq in acquisitions:
            add_acquisition_file_info(sub_id, sub_label, ses_id, ses_label, acq, args.file_type, patient_identifier_keys, data_dict)
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
            # Get this session's acquisitions as an iterator and loop through them
            acquisitions = ses.acquisitions.iter()
            for acq in acquisitions:
                add_acquisition_file_info(sub_id, sub_label, ses_id, ses_label, acq, args.file_type, patient_identifier_keys, data_dict)

# Convert the dict to a pandas dataframe
df = pd.DataFrame.from_dict(data_dict)

# write file

filename = f"{group_label}_{project_label}_{args.file_type}_deid_report.csv"
df.to_csv(filename,index=False, na_rep = 'NA')
