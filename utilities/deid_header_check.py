#!/usr/bin/env python

import argparse
import flywheel
import os
import pandas as pd
import pydicom
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


def add_first_acquisition_header_info(sub_id, sub_label, ses, patient_identifier_keys, data_dict):

    test_acq = None
    # This is the dicom archive file we will extract a dcm file from, or a single dcm file
    test_file = None
    # Find the first acquisition that has a dicom zip file or a .dcm file

    # The actual dcm file we will write to disk temporarily
    # This is extracted / downloaded from the test_file object
    tmp_dcm_file = 'deid_header_check_data.dcm'

    if os.path.exists(tmp_dcm_file):
        raise RuntimeError(f"Temporary file {tmp_dcm_file} exists, something went wrong.")

    for acq in ses.acquisitions.iter():
        if acq.label.lower().startswith('phoenix'):
            continue
        if os.path.exists(tmp_dcm_file):
            break
        for f in acq.files:
            if (f.type == 'dicom'):
                try:
                    f = f.reload()
                    image_type = f.info['ImageType']
                    # Only look at primary images. Some data had derived images from PACS that WERE de-identified
                    # even though the primary images were not. Of course it's possible that the reverse could happen
                    # but the only way to be sure would be to check every acquisition, which results in API timeouts
                    if 'PRIMARY' in [ t.upper() for t in image_type ]:
                        # Should be able to use f.zip_member_count, but this sometimes None
                        # even when the zip file is not empty
                        if (f.name.lower().endswith('.zip')) and f.size > 512:
                            try:
                                test_acq = acq
                                test_file = f
                                fw_dcm = test_file.get_zip_info().members[0]
                                test_file.download_zip_member(fw_dcm.path, tmp_dcm_file)
                            except Exception as e:
                                print(f"Error processing {sub_label}/{ses_label}/{acq_label}/{file_name}")
                                print(f"Cannot download dicom file from zip archive: {e}")
                            break
                        elif f.name.lower().endswith('.dcm') and f.size > 512:
                            try:
                                test_acq = acq
                                test_file = f
                                acq.download_file(test_file.name, tmp_dcm_file)
                            except Exception as e:
                                print(f"Error processing {sub_label}/{ses_label}/{acq_label}/{file_name}")
                                print(f"Cannot download dicom file: {e}")
                            break
                except KeyError:
                    pass

    if not os.path.exists(tmp_dcm_file):
        data_dict['project_id'].append(ses.project)
        data_dict['subject_id'].append(sub_id)
        data_dict['subject_label'].append(sub_label)
        data_dict['session_id'].append(ses_id)
        data_dict['session_label'].append(ses_label)
        data_dict['acquisition_id'].append(pd.NA)
        data_dict['acquisition_label'].append(pd.NA)
        data_dict['file_name'].append(pd.NA)
        data_dict['file_user'].append(pd.NA)
        data_dict['file_created'].append(pd.NA)
        data_dict['header_deidentification_method'].append('NoSuitableDicomFile')
        data_dict['header_has_patient_identifiers'].append(pd.NA)
        data_dict['header_patient_identifiers_populated'].append(pd.NA)
        data_dict['session_checked'].append(False)
        return

    # Important to clearly flag cases where the session was not checked
    session_checked = False

    acq_label = test_acq.label
    acq_id = test_acq.id

    file_name = test_file.name
    file_user = test_file.origin['id']
    file_created = str(test_file.created.date())

    # deid_method from the header, not metadata
    dcm_deid_method = pd.NA
    dcm_has_patient_identifiers = False
    dcm_patient_identifiers_populated = False

    try:
        dcm = pydicom.dcmread(tmp_dcm_file)

        if 'DeidentificationMethod' in dcm:
            dcm_deid_method = dcm['DeidentificationMethod'].value

        # helper to check identifiers in a dataset
        def check_identifiers(ds, patient_identifier_keys):
            has_identifiers = False
            populated = False
            identifier_keys = [id_key for id_key in patient_identifier_keys if id_key in ds]
            for key in identifier_keys:
                element = ds.data_element(key)
                if not element.is_empty:
                    has_identifiers = True
                    if any(char.isalnum() for char in str(element.value)):
                        populated = True
            return has_identifiers, populated

        # check top-level dataset
        has_ids, populated_ids = check_identifiers(dcm, patient_identifier_keys)
        if has_ids:
            dcm_has_patient_identifiers = True
        if populated_ids:
            dcm_patient_identifiers_populated = True

        # check inside OriginalAttributesSequence (0400,0561)
        if 'OriginalAttributesSequence' in dcm:
            for item in dcm.OriginalAttributesSequence:
                if 'ModifiedAttributesSequence' in item:
                    for mod in item.ModifiedAttributesSequence:
                        has_ids, populated_ids = check_identifiers(mod, patient_identifier_keys)
                        if has_ids:
                            dcm_has_patient_identifiers = True
                        if populated_ids:
                            dcm_patient_identifiers_populated = True

        session_checked = True
    except pydicom.errors.InvalidDicomError:
        print(f"Cannot read dicom from {sub_label}/{ses_label}/{acq_label}/{file_name}")
        dcm_deid_method = 'InvalidDicomError'
        dcm_has_patient_identifiers = 'InvalidDicomError'
        dcm_patient_identifiers_populated = 'InvalidDicomError'
    finally:
        if os.path.exists(tmp_dcm_file):
            os.remove(tmp_dcm_file)

    data_dict['project_id'].append(ses.project)
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
    data_dict['session_checked'].append(session_checked)


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 prog="deid_header_check", add_help=False, description='''
Script to check Flywheel DICOM file / archive *contents* for de-identification method and common
patient identifiers.

Output is a CSV file containing results for every DICOM file or DICOM zip archive in the project.
The output file is named group_project_dicom_header_deid_report.csv.

By default, the script iterates over all files in a project, it can take some time to retrieve each
file's data from the server. It can optionally take a list of session IDs, which can be from any combination
of groups and projects. If a session list is provided, the group and project arguments are only used to
name the output, and do not need to correspond to actual group or project labels. Using a session list is
slower, and only recommended if you are testing a small subset of sessions.

What this script does:
     * Iterates over every subject, session or a selected list of sessions
     * Find the first acquisition with a dicom zip file (ignoring PhoenixZipReports and other unreliable files)
     * Downloads the first dicom file from the zip and check its header
     * Reports if identifiers are found
     * Reports if a session could be checked - the last column of the output will be false if the session
       did not contain any data that could be checked

DICOM fields checked: The list of fields to be checked will be printed to the screen when the script is run.

Important output fields:

  header_has_patient_identifiers:
    True if the dicom file contains any of the patient identifier fields, unless the field is empty. If the data
    was de-identified correctly, these fields will exist (they are created if the source data does not contain them)
    but will be empty.

  header_patient_identifiers_populated:
    True if the patient identifier fields contain alphanumeric characters. This is a good indicator that the data was
    not de-identified correctly. To identify false-positives, this will be false if the field does not contain any
    alphanumeric characters. For example, if the PatientName field contains only spaces, or is something like '######'.

  session_checked:
    True if a file could be checked for the session. If this is false, the session did not contain any dicom files that
    could be checked, or the acquisition that was inspected could not be read for some reason.

The dicom files are stored in the current working directory - they will be deleted but the user may
have to manually remove them if the script is interrupted.

The output contains information about the subject, session, acquisition, and file (meaning the dicom
zip archive). The "file_created" field refers to the date the file was uploaded to Flywheel.

The header_ fields pertain to the header of the first DICOM file in the zip archive. This is
distinct from the file's metadata (which can be checked with deid_check.py).

What this script does not do:

    * Check all dicom files in a session. It would take far too long to do this. It looks for the first
      zip archive containing dicom files with the image type PRIMARY. It will not check individual files
      (eg, physio files).

    * Check secondary captures, like segmentations from PACS. Secondary data often uses private
      tags to store information, this script cannot check these effectively. They can also produce
      false negatives because they sometimes do not inherit identifiers from the primary image.

    * Check files that have not run through the Flywheel DICOM classifier. These will not have the necessary
      metadata for the script to work.

    * Check non-DICOM files (eg, NIFTI, JSON). Usually these will inherit identifiers from DICOM files.
      While NIFTI files generally do not contain identifiers, it is possible that subject IDs could
      be encoded in the description field. JSON files can also contain identifiers. If identifiers are
      present in the DICOM files, any files derived from the DICOM must be checked carefully.

    * Check all possible identifiers. The script checks a selection of direct identifiers including
      PatientName, PatientID, PatientAddress, and PatientBirthDate.

    * Validate the de-identification. The script outputs the reported deidentification method, but
      does not check that the de-identification actually happened to the specification of that
      method, beyond checking the selected direct identifiers.

    * Check metadata above the file level, for example it does not check if the Subject container
      contains PII.

    * Check any private tags.

''')
required = parser.add_argument_group('Required arguments')
required.add_argument("group", help="Group label", type=str)
required.add_argument("project", help="Project label", type=str)

optional = parser.add_argument_group('Optional arguments')
optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")
optional.add_argument("-s", "--sessions", help="Text file containing a list of session IDs, one per line.", type=str,
                      default=None)

if len(sys.argv) == 1:
    parser.print_usage()
    parser.exit(status=1, message="Use -h to see full help.\n")

args = parser.parse_args()

fw = flywheel.Client()

# First generate our "data dictionary" that will contain the values we want to track
data_dict = {'project_id': [], 'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[],
             'acquisition_id':[], 'acquisition_label':[], 'file_name':[],'file_user':[],
             'file_created':[], 'header_deidentification_method':[],
             'header_has_patient_identifiers':[], 'header_patient_identifiers_populated':[], 'session_checked':[]}

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

if sessions_fn is not None:

    print(f"Checking sessions listed in {sessions_fn}")

    with open(sessions_fn, 'r') as sessions_io:
        session_ids = [ ses_id.rstrip() for ses_id in sessions_io.readlines()]
    for ses_id in tqdm(session_ids):
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

    print(f"Checking all sessions in {group_label}/{project_label}")

    # Get the project
    project = fw.lookup(f"{group_label}/{project_label}")

    # Note: this is the FW recommended way, but it doesn't let you know the progress very accurately
    # Also doesn't seem to be much faster if at all for project I've tested (few hundred to low thousands)
    # subjects = project.subjects.iter()

    subjects = project.subjects()

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
            add_first_acquisition_header_info(sub_id, sub_label, ses, patient_identifier_keys, data_dict)

# Convert the dict to a pandas dataframe
df = pd.DataFrame.from_dict(data_dict)

# Select all rows where the header has patient identifiers
df_with_identifiers = df[df['header_has_patient_identifiers'] == True]

# Check if any rows in df_with_identifiers have populated identifiers
if not df_with_identifiers.empty:
    filename = f"{group_label}_{project_label}_dicom_zip_header_sessions_with_identifiers.csv"

    if not df_with_identifiers[df_with_identifiers['header_patient_identifiers_populated'] == True].empty:
        print_highlighted_warning(f"%%% ALERT Identifiers were found! %%%\n\nVerify immediately and notify site admin."
                                f"\nWriting a list of sessions with identifiers to:\n"
                                f"    {filename}\n")
    else:
        print_highlighted_warning(f"%%% WARNING Some data may not have been de-identified correctly %%%\n\n."
                                "Identifier fields were found but they appear to not be populated with real information.\n"
                                f"\nWriting a list of sessions with possible identifiers to:\n"
                                f"    {filename}\n")

    df_with_identifiers.to_csv(filename,index=False, na_rep = 'NA')
else:
    print("\nNo identifiers were found in checked sessions\n")

# Find errors
df_session_checked_errors = df[df['session_checked'] == False]

if not df_session_checked_errors.empty:
    print(f"WARNING: Some sessions could not be checked")
    filename = f"{group_label}_{project_label}_dicom_zip_header_sessions_with_errors.csv"
    print(f"Writing a list of sessions that could not be checked to:\n    {filename}\n")
    df_session_checked_errors.to_csv(filename,index=False, na_rep = 'NA')

full_report_fn = f"{group_label}_{project_label}_dicom_zip_header_deid_report.csv"

print(f"Writing a list of all acquisitions tested to:\n    {full_report_fn}\n")

# Sort the DataFrame so that errors and sessions with identifiers are printed first
df_sorted = df.sort_values(by=['header_patient_identifiers_populated', 'subject_label', 'session_label'],
                           ascending=[False, True, True])

# Export to CSV
df_sorted.to_csv(full_report_fn, index=False, na_rep='NA')

