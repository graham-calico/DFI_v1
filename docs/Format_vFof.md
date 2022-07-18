<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# File Format: video file-of-files

This page provides specifications for the **video file-of-files**, used by scripts in the Primary
Analysis step.  This file lists the Google Cloud storage location for each and every 10-minute video
file from an entire Digital Frailty study.

Each line should list the path for **one** video file,
with newline characters (`\n`) separating the lines.  The files should have blob names (i.e. paths)
following the [**specifications for video file naming**](Spec_vidFiles.md).  Here is an example:

```
gs://bucket_name/study/specific/directory_path/device_id/some_sub_dir/2021/08/02/18.10.mp4
```

The above path points to a video collected on February 8th, 2021, at 6:10 pm (starting time).
Some features of this path must be correctly represented in the [**config file**](Format_aConfig.md):
- The `bucket_name` (name of the Google bucket in which these files are stored) should be bound to
the `input_mov_bucket` variable.
- The `study/specific/directory_path` can contain one or more directory levels, and should be bound to
the `input_mov_folder` variable.

Some features of this path must also be correctly represented in the [**device mapping file**](Format_DevMap.md):
- The `device_id/some_sub_dir` portion of the path must match an entry for **Device/Cage ID** in that file.
This portion of the path may be one or several directory layers.  But it must be immediately preceeded by
the `study/specific/directory_path` and must be immediately followed by a directory indicating the year
in which the data were collected (here, `2021`).
