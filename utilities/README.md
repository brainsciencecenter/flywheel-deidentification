# Utilities

Scripts to help identify de-identification issues. These require the [Flywheel
SDK](https://pypi.org/project/flywheel-sdk/).


## deid_metadata_check.py

`deid_metadata_check.py` reads a project's acquisition and file metadata to look for
identifiers and records of de-identification. It is somewhat slow and may take many
minutes to hours for very large projects.

The script checks both acquisition and file containers. Some older import code added DICOM
header information to the `metadata` attribute in the acquisition container. This appears
to have been deprecated and now dicom metadata is found in the file `info` attribute.

### Output

Examples here assuming dicom files checked (the default). The label "dicom" in the output
files will change if other file types are selected.

These files are always produced:

```
{group}_{project}_acquisition_metadata_report.csv
{group}_{project}_dicom_file_metadata_deid_report.csv
```

If identifiers are found, additional files are written, these are a subset of the full
report

```
{group}_{project}_acquisition_metadata_with_identifiers.csv
{group}_{project}_dicom_file_metadata_with_identifiers.csv
```

Acquisitions with non-null `metadata` attributes are listed in

```
{group}_{project}_acquisitions_with_metadata_attribute.csv
```



Output columns for file checks:

```
subject_id
subject_label
session_id
session_label
acquisition_id
acquisition_label
file_name
```

Flywheel info about the subject / session / acquisition containing the file

```
file_user
```

The user who created the file. This might be a UID for a device - files created by gears
or by dicom connectors. If it was a manual upload via web or CLI, the username will be
shown.

```
file_created
```

File creation date - when the file was created, which is not necessarily the scan date.

```
file_has_info
```

TRUE if the file has an info dictionary, FALSE otherwise. This will be FALSE if the file
was not successfully run through the dicom classifier gear for some reason. This can
happen for several reasons, including bad data, non-imaging data that is intentionally not
classified, or othet failures with the dicom classifier process.

```
file_deidentification_method
```

The string found in the info dictionary under `DeidentificationMethod`. This is derived
from the DICOM tag (0012,0063), keyword DeidentificationMethod. It should ordinarily be
set to "Penn_BSC_profile_v1.0" or "Penn_BSC_profile_v3.0". If it is "NA", no
deidentification method was recorded in the data.

```
file_has_patient_identifiers
```

TRUE if the file has any of the direct patient identifiers tested in the script. See
script for details. Empty fields are not counted.

```
file_patient_identifiers_populated
```

TRUE if any of the patient ID fields are populated with alphanumeric characters. This
catches some cases where patient fields exist, but are populated with empty space or
metacharacters like "^^^^^^".

If your project deliberately contains any alphanumeric values in these fields, this
column will not be useful, and you will need to modify the script to check fields that
shouldn't exist, and to check fields that do exist conform to expectations (eg the format
of a coded value in PatientID).

```
found_fields
```

A slash-separated list of dicom keywords found in the file metadata.


## deid_header_check.py

A similar script to `deid_metadata_check.py`, but this checks DICOM files directly instead of
metadata. It is therefore slower and can download a substantial amount of data for large
projects.


## dicom_upload_device.py

`dicom_upload_device.py` outputs information about the device or user who uploaded a
particular DICOM file / archive. This can be helpful to distinguish manually uploaded
files from those produced from a dicom connector.

The device ID is also output by `deid_check.py`, but this script runs faster so if you
want to check only manual uploads, you can find them with this script and then pass
sessions to `deid_check.py` with `--sessions`. Note though that selecting individual
sessoins in this way is slower *per session* than iterating over the whole project, so it
only really makes sense if you want to check a small proportion of a project.
