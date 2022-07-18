<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# File Format: device & ID mappings

This page provides specifications for the **device mapping file**, used by the `dfiCalculateValues.py`
script.  For each stretch of time across which a mouse was being filmed for the purpose of calculating
a Digital Frailty Index score, an entry is provided in this file.  Each entry includes the mouse's ID
and the start & stop times for each DFI time interval (~a week), along with the device ID for the
camera/cage that was used to collect the video.

## Required File Components

**Mouse ID:** The unique identifier for each mouse in the study.  There can be multiple
entries in this file per mouse: each entry should correspond to a block of time designated
for a single DFI measurement (recommended: ~a week).  These IDs should be compliant with
linux file name conventions (i.e. no white space!).

**Start/Stop Times:** When recording starts and stops for this DFI measurement.  These do
not need to precisely line up with when cages are inserted into/removed from the rack, but
including time when the cage is empty or the slot is occupied by a different mouse will
yield eroneous or misleading results.  The time zone here should match that used for
naming the video files & their paths (see [**video file storage specifications**](Spec_vidFiles.md)).

Date/times should have the following format: `yyyy-mm-ddThh:nn:ss.fffZ`, where `yyyy` is the four-digit year;
`mm` is the two-digit month; `dd` is the two-digit day; `hh` is the two-digit hour, in 24-hour notation;
`nn` is the two-digit minute; `ss` is the two-digit second; `fff` is the fraction of a second.  Example:
`2021-05-24T17:03:18.038Z`.

**Device/Cage ID:** This system is designed to operate on video files stored in Google Cloud buckets 
and named and organized according to to [this ruberic](Spec_vidFiles.md).  The device or cage ID
corresponds to the directory in which date-specific video will be found.  

**Optional-Format Components:** Not all columns are used by this softward system, and they can be used
to record information the will be useful to the scientist using the data (see below).

## Overall format

This file is tab-separated text (.tsv), with `\n` line breaks.  There is no header line: each line
corresponds to a block of time for which a DFI score will be calculated.  Generally, these time blocks
are ~a week long.  They do not need to correspond 1:1 to intervals of video recording.  For instance,
if video was collected continuously for a month for a mouse in the same cage, four time-consecutive entries
could be provided in this file to produce four consecutive DFI scores.

| | |
| :---- | :------ |
|   Column 1   | Optional content (generally used for cage slot & rack info) |
| **Column 2** | **Device/Cage ID** |
| **Column 3** | **Start time** |
| **Column 4** | **End time** |
| **Column 5** | **Mouse ID** |
|  Columns 6+  | Optional (can be used for groups, genotypes, treatment arms, etc.) |


