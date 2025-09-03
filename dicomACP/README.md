# Dicom Attribute Confidentiality Profiles

This directory contains the DICOM Attribute Confidentiality Profiles as defined in PS3.15
of the DICOM Standard. The latest version of the standard can be found at

https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_e.html

The files in this directory are based on version 2025c. Scripts have been generated with
ChatGPT 5, and the output has not been verified line-by-line against the source. It
appears to be complete but the accuracy cannot be guaranteed. Please verify carefully
before using in production.


## Overview of DICOM Attribute Confidentiality Profiles

The DICOM Standard defines several standard profiles for de-identification of DICOM data.
The "basic profile" removes or obscures around 500 standard DICOM attributes, and includes
the removal of all "private" attributes.

There are sub-profiles that retain some information including "safe" private attributes
(definition safety is undefined), UIDs, device identity, dates, and institution identity.


## Code for parsing the profiles from the dicom standard

* `get_dicom_confidentiality_profile_attributes.py` - a script to extract the profile
  table from the [DICOM
  standard](https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html#table_E.1-1).
  It reads from the HTML, and writes to CSV or Excel format. The dicom standard
  is available in other formats, including XML, which might be easier to parse.

* `dicom_part15_table_E1-1.csv` - the Basic Profile (Table E.1-1) in CSV format, from
  running the above script, plus some minor spacing corrections. See
  [here](https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html#table_E.1-1a)
  for the definition of the codes in the "Action" columns.


## Checking data against the profiles with dcmtk

For convenience, some lists of tags for the `dcmdump` program from
[dcmtk](https://dicom.offis.de/dcmtk.php.en) are provided. Note that these lists do not
include any private tags.

The wildcard tags (50xx,xxxx) (60xx,3000) (60xx,4000) were expanded by ChatGPT 5. To print
attributes in the basic profile, do:
```
dcmdump @dcmdump_basic_profile_public_attributes.txt +s +p <file.dcm>
```
Note that the basic profile is quite expansive, and the output will be very long.

To check a more limited set of tags (anything that has a "keep" action in any profile), do:
```
dcmdump @dcmdump_keep_any_profile_public_attributes.txt +s +p <file.dcm>
```

