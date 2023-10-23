#!/usr/bin/env python

import argparse
import flywheel
import pandas as pd

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 prog="deid_check", add_help=True, description='''
Script to tabulate the device information about all DICOM file containers in a project. The device
ID is also given in deid_check.py, but that script requires more information retrieval. Most
de-identification failures come from user uploads, so this script can be used to identify those
files for closer inspection.
''')
required = parser.add_argument_group('Required arguments')
required.add_argument("group", help="Group label", type=str)
required.add_argument("project", help="Project label", type=str)
args = parser.parse_args()

fw = flywheel.Client()

# First generate our "data dictionary" that will contain the values we want to track
data_dict = {'subject_id':[], 'subject_label':[], 'session_id':[], 'session_label':[],
             'acquisition_id':[], 'acquisition_label':[], 'file_name':[],'file_creator_id':[],
             'file_creator_name':[], 'file_creator_type':[], 'file_created':[]}

group_label = args.group
project_label = args.project

# Get the project
project = fw.lookup(f"{group_label}/{project_label}")

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
            # Get the acquisition's label
            acq_label = acq.label
            acq_id = acq.id
            # Loop over all files, but check only dicom
            # Usually only one dicom per acquisition but not always
            for f in acq.files:
                if f.type != 'dicom':
                    continue
                file_name = f.name
                # get origin containing id, method, name, type, via
                file_origin = f.origin
                file_origin_id = file_origin['id']
                file_origin_name = file_origin['name']
                file_origin_type = file_origin['type']
                file_created = str(f.created.date())

                data_dict['subject_id'].append(sub_id)
                data_dict['subject_label'].append(sub_label)
                data_dict['session_id'].append(ses_id)
                data_dict['session_label'].append(ses_label)
                data_dict['acquisition_id'].append(acq_id)
                data_dict['acquisition_label'].append(acq_label)
                data_dict['file_name'].append(file_name)
                data_dict['file_creator_id'].append(file_origin_id)
                data_dict['file_creator_name'].append(file_origin_name)
                data_dict['file_creator_type'].append(file_origin_type)
                data_dict['file_created'].append(file_created)

# Convert the dict to a pandas dataframe
df = pd.DataFrame.from_dict(data_dict)

# write file

filename = f"{group_label}_{project_label}_dicom_file_origin_report.csv"
df.to_csv(filename,index=False, na_rep = 'NA')
