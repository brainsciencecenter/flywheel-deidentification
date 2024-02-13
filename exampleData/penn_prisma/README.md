# Example data with pseudo-PHI

The example data is a phantom MRI image series with pseudo-PHI. There's no real patient
information.

## Data source and licensing

This data is a phantom acquired on the SC3T scanner for protocol validation in 2022.


## Data contents

A localizer, a T1w series, an HCP-style SpinEchoFieldMap field map source image, and an
SBRef BOLD series are included.


## Expected behavior

After successful de-identification, patient identifiers should be removed, and the tag
DeidentificationMethod (0012,0063) should say "Penn_BSC_profile_v3.0".


## Command line ingest

```
cd flywheel-deidentification/exampleData/penn_prisma
fw ingest dicom \
    --subject IngestTest \
    --session MR1 \
    dicom YourGroup DeIdIngestPrismaExample
```

After ingest, click on the information button to see metadata extracted from the DICOM headers

In particular, see that the DeidentificationMethod is correct and identifying patient
information is removed.


## Comparing the original and de-identified data.

The de-identified acquisition can be downloaded as a .zip file. See `dicomDeidentified/`
for reference.

Compare the first slice header files with DCMTK's `dcmdump`:

```
dcmdump dicom/7_anat_T1w/7_anat_T1w_001.dcm > originalHeader.txt
dcmdump dicomDeidentified/7_anat_T1w/7_anat_T1w_001.dcm > flywheelHeader.txt
```

Private tags are unaltered by the profile. For example, the Siemens CSA header information
in field (0029,1010) should exist in both files.
