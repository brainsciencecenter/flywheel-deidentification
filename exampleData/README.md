# Example data with pseudo-PHI

The example data is a body MRI image series with pseudo-PHI. There's no real patient
information.

## Data source and licensing

The data is derived from the [Evaluation dataset from the Cancer Imaging Archive
(TCIA)](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=80969777).

If using the data in any publication or presentation, please cite appropriately according
to the data set's [Citations & Data Usage
Policy](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=80969777#80969777a67b45d26c6f492fa9a3a288894ac6c7).


## Data contents

The `dicom/` folder contains a single body MRI with pseudo-PHI. It has been modified to
further include PatientAddress (0010,1040) and PatientTelephoneNumbers (0010,2154).


## Expected behavior

After successful de-identification, patient identifiers should be removed, and the tag
DeidentificationMethod (0012,0063) should say "Penn_BSC_profile_v3.0".


## Command line ingest

```
fw ingest dicom \
    --subject IngestTest \
    --session MR1 \
    dicom YourGroup DeIdIngestExample
```

After ingest, click on the information button to see metadata extracted from the DICOM headers

![Flywheel web session acquisitions view](/exampleData/screenCaps/session_acquisitions.jpg)

In particular, see that the DeidentificationMethod is correct and identifying patient
information is removed.

![Flywheel file information window](/exampleData/screenCaps/metadata_info_deidmethod.jpg)

![Flywheel file information window 2](/exampleData/screenCaps/metadata_info_patient.jpg)


## Comparing the original and de-identified data.

The de-identified acquisition can be downloaded as a .zip file. See `dicomDeidentified/`.

Compare the first slice header files with DCMTK's `dcmdump`:

```
dcmdump dicom/1-01.dcm > originalHeader.txt
dcmdump dicomDeidentified/2.25.11855366655957802449504060070008831478.MR.dcm > flywheelHeader.txt
```

Tags in the source data and profile are replaced with an empty value, eg (0010,0010)
PatientName becomes

```
	(0010,0010) PN (no value available)
```

Tags that exist in the profile but not in the source data are created, and set to an empty
value. For example, (0010,1001) OtherPatientNames exists in the de-identified header as

```
    (0010,1001) PN (no value available)
```

Private tags are unaltered by the profile. Both headers contain the private tags,
unchanged, for example

```
(0013,0010) LO [CTP]                                    #   4, 1 PrivateCreator
(0013,1010) LO [Pseudo-PHI-DICOM-Data]                  #  22, 1 Unknown Tag & Data
(0013,1013) LO [87009668]                               #   8, 1 Unknown Tag & Data
```
