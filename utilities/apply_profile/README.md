# Simulating the Flywheel site profile

Originally, Flywheel had an option to write data to a zip file rather than ingesting to
the site. This let you test the de-identification profile on your own system before
uploading to Flywheel. This option has now been removed, and there is no way to apply the
profile locally.

The script `simulate_apply_profile.py` in this directory simulates the Flywheel site
profile de-identification. It reads a profile in YAML format, and applies it to DICOM
files in a directory, writing the modified files to a new directory or modifying them in
place.

Note that this is not the actual Flywheel code, and there may be differences in behavior.
It is a best guess of what Flywheel does. After running the script, you can use `dcmdump`
to see if there's any remaining patient information. See the `dicomACP` directory for
lists of public tags to check.