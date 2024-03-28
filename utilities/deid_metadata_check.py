#!/usr/bin/env python

import argparse
import flywheel
import pandas as pd
import sys

from tqdm import tqdm

def print_highlighted_warning(message):
    box_width = 80
    padding = 3
    text_width = box_width - 2 * padding - 2  # 2 for the asterisks on each side
    lines = message.split('\n')
    max_line_width = max(len(line) for line in lines)
    box_width = max_line_width + 2 * padding + 2  # 2 for the asterisks on each side
    print()
    print('*' * box_width)
    for line in lines:
        print('*' + ' ' * padding + line.ljust(max_line_width) + ' ' * padding + '*')
    print('*' * box_width)
    print()


def check_for_sensitive_tags(info_dict):
    """Check for sensitive keys in an bids-ish info dict.

    Useful for info from file.info and acquisition.metadata."""
    has_patient_identifiers = False
    has_patient_identifiers_populated = False
    if info_dict is not None and info_dict:
        identifier_keys = [id_key for id_key in patient_identifier_keys
                           if id_key in info_dict]
        for key in identifier_keys:
            value_string = str(info_dict[key])
            if len(value_string) > 0:
                has_patient_identifiers = True
                # Check if file_info[key] contains alphanumeric characters
                if any(char.isalnum() for char in value_string):
                    has_patient_identifiers_populated = True
    return has_patient_identifiers, has_patient_identifiers_populated


def add_acquisition_file_info(project_id, sub_id, sub_label, ses_id, ses_label, acq, select_file_type, patient_identifier_keys, data_dict):
    acq_label = acq.label
    acq_id = acq.id

    # The acquisition container can have a "metadata" field storing dicom data
    acq_ = acq.reload()
    acq_has_patient_identifiers, acq_patient_identifiers_populated = check_for_sensitive_tags(
        acq_.get("metadata")
    )
    acq_data_dict['project_id'].append(project_id)
    acq_data_dict['subject_id'].append(sub_id)
    acq_data_dict['subject_label'].append(sub_label)
    acq_data_dict['session_id'].append(ses_id)
    acq_data_dict['session_label'].append(ses_label)
    acq_data_dict['acquisition_id'].append(acq_id)
    acq_data_dict['acquisition_label'].append(acq_label)
    acq_data_dict['acquisition_has_metadata'].append("metadata" in acq_)
    acq_data_dict['acquisition_has_patient_identifiers'].append(acq_has_patient_identifiers)
    acq_data_dict['acquisition_patient_identifiers_populated'].append(acq_patient_identifiers_populated)

    for f in acq.files:
        if select_file_type != 'all' and f.type != select_file_type:
            continue
        f = f.reload()
        file_name = f.name
        file_user = f.origin['id']
        file_created = str(f.created.date())
        file_info = f.info
        file_type = f.type
        file_deid_method = f.info.get('DeidentificationMethod')
        file_has_info = True
        if not file_info:
            # This happens if the file has not had any classifiers run on it
            file_has_info = False
        file_has_patient_identifiers, file_patient_identifiers_populated = check_for_sensitive_tags(
            f.info
        )
        data_dict['project_id'].append(project_id)
        data_dict['subject_id'].append(sub_id)
        data_dict['subject_label'].append(sub_label)
        data_dict['session_id'].append(ses_id)
        data_dict['session_label'].append(ses_label)
        data_dict['acquisition_id'].append(acq_id)
        data_dict['acquisition_label'].append(acq_label)
        data_dict['file_name'].append(file_name)
        data_dict['file_type'].append(file_type)
        data_dict['file_user'].append(file_user)
        data_dict['file_created'].append(file_created)
        data_dict['file_has_info'].append(file_has_info)
        data_dict['file_deidentification_method'].append(file_deid_method)
        data_dict['file_has_patient_identifiers'].append(file_has_patient_identifiers)
        data_dict['file_patient_identifiers_populated'].append(file_patient_identifiers_populated)


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 prog="deid_metadata_check", add_help=False, description='''
Script to check Flywheel DICOM file / archive *metadata* for de-identification method and common
patient identifiers.

Note that this script does not check the DICOM files themselves. It checks the metadata attached
to the file container in the Flywheel system.

Output is a CSV file containing results for every DICOM file or DICOM zip archive in the project.
The output file is named group_project_dicom_deid_report.csv.

By default, the script iterates over all dicom files in a project, it can take some time to retrieve each
file's data from the server. It can optionally take a list of session IDs, which can be from any combination
of groups and projects. If a session list is provided, the group and project arguments are only used to
name the output, and do not need to correspond to actual group or project labels. Using a session list is
slower, and only recommended if you are testing a small subset of sessions.

What this script does:
     * Iterates over every subject, session, acquisition, file container.
     * If file is DICOM, check its metadata for the existence of common direct identifiers in
       standard DICOM fields, and also check if a deidentification method is recorded.
     * Optionally, file types other than DICOM can be checked.

What this script does not do:
    * Check the file contents. This script checks for metadata that is placed into the file container on Flywheel.
      To check for identifiers in DICOM archives, use the dicom_deid_header_check.py script.

    * Check all possible identifiers. The script checks a selection of direct identifiers including
      PatientName, PatientID, PatientAddress, and PatientBirthDate.

    * Validate the reported de-identification method. The script outputs the reported deidentification method,
      but does not check that the de-identification actually happened to the specification of that
      method.

    * Check metadata above the file level, for example it does not check if the Subject container
      contains PII. Often these will only be populated through DICOM import.

    * Check any private tags or other custom metadata.

''')
required = parser.add_argument_group('Required arguments')
required.add_argument("group", help="Group label", type=str)
required.add_argument("project", help="Project label", type=str)

optional = parser.add_argument_group('Optional arguments')
optional.add_argument("-h", "--help", action="help", help="show this help message and exit")
optional.add_argument("-s", "--sessions", help="Text file containing a list of session IDs, one per line. " \
                      "Use this to check a subset of sessions in the project.", type=str, default = None)
optional.add_argument("-t", "--file-type", help="File type to check, or 'all' to check all types", type=str, default="dicom")
optional.add_argument("-k", "--api-key", help="flywheel api token. needed for fw-beta", type=str)

if len(sys.argv) == 1:
    parser.print_usage()
    parser.exit(status=1, message="Use -h to see full help.\n")

args = parser.parse_args()

if args.api_key:
    fw = flywheel.Client(args.api_key)
else:
    fw = flywheel.Client()

# First generate our "data dictionary" that will contain the values we want to track
data_dict = {'project_id': [], 'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[], 'acquisition_id':[],
             'acquisition_label':[], 'file_name':[], 'file_type':[], 'file_user':[], 'file_created':[], 'file_has_info':[],
             'file_deidentification_method':[], 'file_has_patient_identifiers':[], 'file_patient_identifiers_populated':[]}
acq_data_dict = {
    'project_id': [], 'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[], 'acquisition_id':[],
    'acquisition_label':[], 'acquisition_has_metadata':[], 'acquisition_has_patient_identifiers':[], 'acquisition_patient_identifiers_populated':[]}

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

# Print standard disclaimer
print("\n" + '''IMPORTANT: This script cannot detect all potential sources of PII.
Please see help (-h) for more information on its limitations.
''')

# Print out the list of patient identifiers we will check
print("Checking for patient identifiers in the following fields:")
for id_key in patient_identifier_keys:
    print(f"  {id_key}")

print("")

# Print out the list of file types we will check
print(f"Checking files of type: {args.file_type}")

if sessions_fn is not None:

    print(f"Checking sessions listed in {sessions_fn}")

    with open(sessions_fn, 'r') as sessions_io:
        session_ids = [ ses_id.rstrip() for ses_id in sessions_io.readlines()]
    for ses_id in tqdm(session_ids):
        ses = fw.get(ses_id)
        sub = ses.subject
        project_id = ses.project
        sub_label = sub.label
        sub_id = sub.id
        ses_label = ses.label
        acquisitions = ses.acquisitions.iter()
        for acq in acquisitions:
            add_acquisition_file_info(project_id, sub_id, sub_label, ses_id, ses_label, acq, args.file_type,
                                      patient_identifier_keys, data_dict)
else:

    print(f"Checking all sessions in {group_label}/{project_label}")

    # Get the project
    project = fw.lookup(f"{group_label}/{project_label}")

    # Note we get a list here instead of using a generator so we can track progress
    # We use the generators at the session and acquisition levels
    subjects = project.subjects()

    project_id = project.id

    # Loop over the subjects
    for sub in tqdm(subjects):
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
                add_acquisition_file_info(project_id, sub_id, sub_label, ses_id, ses_label, acq, args.file_type,
                                          patient_identifier_keys, data_dict)

# Convert the dict to a pandas dataframe
df = pd.DataFrame.from_dict(data_dict)
acq_df = pd.DataFrame.from_dict(acq_data_dict)

output_file_prefix = f"{group_label}_{project_label}_{args.file_type}_file_metadata"

# Select all rows where the header has patient identifiers
df_with_identifiers = df[df['file_has_patient_identifiers'] == True]
acq_df_with_identifiers = acq_df[acq_df['acquisition_has_patient_identifiers'] == True]

# Check if any rows in df_with_identifiers have populated identifiers
all_ok = df_with_identifiers.empty and acq_df_with_identifiers.empty
if not all_ok:
    if not df_with_identifiers.empty:
        filename = f"{output_file_prefix}_with_identifiers.csv"

        if not df_with_identifiers[df_with_identifiers['file_patient_identifiers_populated'] == True].empty:
            print_highlighted_warning(f"%%% ALERT Identifiers were found! %%%\n\nVerify immediately and notify site admin."
                                    f"\nWriting a list of sessions with identifiers to:\n"
                                    f"    {filename}\n")
        else:
            print_highlighted_warning(f"%%% WARNING Some data may not have been de-identified correctly %%%\n\n."
                                    f"Identifier fields were found but they appear to not be populated with real information.\n"
                                    f"\nWriting a list of sessions with possible identifiers to:\n"
                                    f"    {filename}\n")

        df_with_identifiers.to_csv(filename,index=False, na_rep = 'NA')
    if not acq_df_with_identifiers.empty:
        acq_filename = f"{output_file_prefix}_acquisitions_with_identifiers.csv"

        if not df_with_identifiers[df_with_identifiers['acquisition_patient_identifiers_populated'] == True].empty:
            print_highlighted_warning(f"%%% ALERT Identifiers were found! %%%\n\nVerify immediately and notify site admin."
                                    f"\nWriting a list of sessions with identifiers to:\n"
                                    f"    {acq_filename}\n")
        else:
            print_highlighted_warning(f"%%% WARNING Some data may not have been de-identified correctly %%%\n\n."
                                    f"Identifier fields were found but they appear to not be populated with real information.\n"
                                    f"\nWriting a list of sessions with possible identifiers to:\n"
                                    f"    {acq_filename}\n")

        acq_df_with_identifiers.to_csv(acq_filename,index=False, na_rep = 'NA')
else:
    print("\nNo identifiers were found in checked files\n")

# Find errors
df_file_missing_info = df[df['file_has_info'] == False]

if not df_file_missing_info.empty:
    print(f"WARNING: Some files could not be checked because they have no info")
    filename = f"{output_file_prefix}_with_missing_info.csv"
    print(f"Writing a list of sessions that could not be checked to: {filename}\n")
    df_file_missing_info.to_csv(filename,index=False, na_rep = 'NA')

full_report_fn = f"{output_file_prefix}_deid_report.csv"

print(f"Writing a list of all files tested to:\n    {full_report_fn}\n")

# Sort the DataFrame so that errors and sessions with identifiers are printed first
df_sorted = df.sort_values(by=['file_patient_identifiers_populated', 'subject_label', 'session_label'],
                           ascending=[False, True, True])

# Export to CSV
df_sorted.to_csv(full_report_fn, index=False, na_rep='NA')


# Find sessions with the mysterious "metadata" field present
acq_df_has_metadata = acq_df[acq_df['acquisition_has_metadata']]

if not df_file_missing_info.empty:
    print(f"WARNING: Some acquisitions contained the 'metadata' field")
    filename = f"{output_file_prefix}_acqs_with_metadata.csv"
    print(f"Writing a list of acquisitions with 'metadata' to: {filename}\n")
    acq_df_has_metadata.to_csv(filename, index=False, na_rep='NA')

full_report_fn = f"{output_file_prefix}_acquisition_metadata_report.csv"

print(f"Writing a list of all acquisitions tested to:\n    {full_report_fn}\n")

# Sort the DataFrame so that errors and sessions with identifiers are printed first
acq_df_sorted = acq_df.sort_values(by=['acquisition_patient_identifiers_populated', 'subject_label', 'session_label'],
                           ascending=[False, True, True])

# Export to CSV
acq_df_sorted.to_csv(full_report_fn, index=False, na_rep='NA')
