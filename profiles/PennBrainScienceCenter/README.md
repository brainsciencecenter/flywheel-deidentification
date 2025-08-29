# Penn Brain Science Center de-identification profile

The site profile `de-id_upenn_Penn_BSC_profile_v4.0_20250829.yaml` is the "site profile"
used to deidentify all data imported to Flywheel.

## Version history

### 4.0

Add removal of tags that have been problematic after the XA upgrades to the scanners:

- OrderEnteredBy
- OrderEntererLocation
- OrderCallbackPhoneNumber
- OriginalAttributesSequence
- RequestAttributesSequence

PatientSize is no longer removed.

We now set PregnancyStatus to 4 (unknown) rather than an empty string.


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

Check the Flywheel documentation for the best practices on testing and verifying
de-identification.