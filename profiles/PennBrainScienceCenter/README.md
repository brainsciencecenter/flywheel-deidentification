# Penn Brain Science Center de-identification profile

The site profile `de-id_upenn_Penn_BSC_profile_v3.0_20201111A.yaml` is used to deidentify
all data imported to Flywheel by default.

The other file
`fw_PHI_cleanup_deployment_de-id_upenn_Penn_BSC_profile_v3.0_20201111A.yaml` has
additional options set for importing ZIP archives, which may contain a mixture of DICOM
and non-DICOM files.


## Version history

### 3.0

Allow patient weight to be stored in the Flywheel database and in the DICOM attribute
(0010, 1030). Note that Siemens scanners additionally store this information in
the private header, which we do not modify with this profile.

### 2.0

Allow patient age in years to be stored in Flywheel and in the DICOM files.

Flywheel computes the patient age in years from the patient date of birth, and
then includes this information in the reaped / imported DICOM headers. Patient
DOB will still be removed, only age as an integer number of years is recorded.

Age in years is not a named identifier under HIPAA, except for patients aged 90
or older. Special handling of these cases will be required. The profile itself
does **not** handle these differently.

### 1.0

As used by the reaper on HUP6 since November 2019.


## Verifying de-identification

To test the deidentification profile, use `fw deid test`. This will produce a CSV file
with the keywords and values removed from a data set.

After ingest, you can download and examine dicom images with gdcmscanner.

  gdcmscanner -p -r -d  /path/to/flywheel/data -t 0012,0063 | more

You should get output like this:

done retrieving file list <NUMBER OF FILES> files found.
Values:
Penn_BSC_profile_v3.0
Mapping:
Filename: /path/to/some/file.dcm (could be read)
(0012,0063) -> [Penn_BSC_profile_v3.0 ]


Each file should have "Penn_BSC_profile_v3.0" for tag
(0012,0063). This tells you that the de-identification profile was
applied to each file.

If you want to check the full set of tags to empty, you can do

  gdcmscanner -p -r -d /path/to/flywheel/data \
  -t 0008,0050 -t 0008,0090 -t 0008,0092 -t 0008,0094 -t 0008,0096 \
  -t 0008,009c -t 0008,009d -t 0008,1048 -t 0008,1049 -t 0008,1050 \
  -t 0008,1052 -t 0008,1060 -t 0008,1062 -t 0008,1080 -t 0010,0010 \
  -t 0010,0020 -t 0010,0021 -t 0010,0030 -t 0010,0032 \
  -t 0010,0033 -t 0010,0034 -t 0010,0050 -t 0010,0101 -t 0010,1000 \
  -t 0010,1001 -t 0010,1002 -t 0010,1005 -t 0010,1020 \
  -t 0010,1021 -t 0010,1040 -t 0010,1050 -t 0010,1060 -t 0010,1080 \
  -t 0010,1081 -t 0010,1090 -t 0010,1100 -t 0010,2000 -t 0010,2110 \
  -t 0010,2150 -t 0010,2152 -t 0010,2154 -t 0010,2155 -t 0010,2160 \
  -t 0010,2180 -t 0010,21a0 -t 0010,21b0 -t 0010,21c0 -t 0010,21d0 \
  -t 0010,21f0 -t 0010,2203 -t 0010,2297 -t 0010,2298 -t 0010,2299 \
  -t 0010,4000 -t 0032,1030 -t 0032,1031 -t 0032,1032 -t 0038,0050 \
  -t 0038,0300 -t 0038,0500 -t 0038,0100 -t 0040,0006 -t 0040,000b \
  -t 4008,0114 -t 0040,3001 -t 0040,1400 | more

This will print the same summary of values, followed by a mapping for
each file. In this case you will want to see that no values are found
except for an empty string.

Values:

Mapping:
Filename: /path/to/some/file.dcm (could be read)
(0008,0050) -> []
(0008,0090) -> []
(0008,0092) -> []
(0008,0094) -> []
(0008,0096) -> []
(0008,009c) -> []
(0008,009d) -> []
(0008,1048) -> []
(0008,1049) -> []
(0008,1050) -> []
(0008,1052) -> []
(0008,1060) -> []
(0008,1062) -> []
(0008,1080) -> []
(0010,0010) -> []
(0010,0020) -> []
(0010,0021) -> []
(0010,0030) -> []
(0010,0032) -> []
(0010,0033) -> []
(0010,0034) -> []
(0010,0050) -> []
(0010,0101) -> []
(0010,1000) -> []
(0010,1001) -> []
(0010,1002) -> []
(0010,1005) -> []
(0010,1020) -> []
(0010,1021) -> []
(0010,1040) -> []
(0010,1050) -> []
(0010,1060) -> []
(0010,1080) -> []
(0010,1081) -> []
(0010,1090) -> []
(0010,1100) -> []
(0010,2000) -> []
(0010,2110) -> []
(0010,2150) -> []
(0010,2152) -> []
(0010,2154) -> []
(0010,2155) -> []
(0010,2160) -> []
(0010,2180) -> []
(0010,21a0) -> []
(0010,21b0) -> []
(0010,21c0) -> []
(0010,21d0) -> []
(0010,21f0) -> []
(0010,2203) -> []
(0010,2297) -> []
(0010,2298) -> []
(0010,2299) -> []
(0010,4000) -> []
(0032,1030) -> []
(0032,1031) -> []
(0032,1032) -> []
(0038,0050) -> []
(0038,0100) -> []
(0038,0300) -> []
(0038,0500) -> []
(0040,0006) -> []
(0040,000b) -> []
(0040,1400) -> []
(0040,3001) -> []
(4008,0114) -> []
