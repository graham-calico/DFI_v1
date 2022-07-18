<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# DFI: Primary Analysis

This page provides instructions for the Primary Analysis phase of digital frailty: 
the initial analysis of video files.
In a "map-reduce" framework, this corresponds to a "map" function: it will turn each 
video file into a set of number-based
files that will be used by the downstream analyses.

This system is designed to operate on video files stored in Google Cloud buckets and named 
and organized according to to [this ruberic](Spec_vidFiles.md).  It is written to use
[SLURM-GCP](https://github.com/SchedMD/slurm-gcp) for the deployment of tasks.  Please see
the [SLURM-GCP documentation](https://github.com/SchedMD/slurm-gcp) for instructions on
how to create a cluster.  

Given the high-throughput nature of this task and *current* cost and
availability of Google Cloud resources, I *currently* (2022) recommend a cluster
with ***many*** pre-emptible, CPU-based compute nodes in the same region as your video-file 
storage bucket.  A sample config file appropriate to this task is provided (`sampleSlurmGcpConfig.tfvars`).
After editing the values assigned to `cluster_name` and `project` variables at the top of the file,
you should be able to create and destroy clusters in your Google Cloud Shell terminal as follows:

```bash
$ terraform apply -var-file=sampleSlurmGcpConfig.tfvars
$ terraform destroy -var-file=sampleSlurmGcpConfig.tfvars
```

*Hint:* pay special attention to the CPU specification and threading availability on your machines.
The *current* (2022) compute-node specification in the sample config file should match up with the
default value given to the Slurm `--cpus-per-task` flag provided by `createRunScripts1st.py` (see **"Set-up for a data set"** below), but if
VM hardware is modified, care should be taken that CPUs are being used efficiently.


## Installation

Upload this repository to the **login node** of your Slurm-GCP cluster and navigate
to the `PrimaryAnalysis` directory.  Use this command to set up your environment and
install the needed dependencies:

```bash
$ ./setupEnv.sh
```

The set-up script installs **python v3.7.8** and its dependencies in a manner that it can
be accessed by the Slurm-GCP compute nodes as well as the login node.  In order to access
this version of python using the command `python3.7`, load its module:

```bash
$ module load python/3.7.8
```

One of the tasks that the set-up script performs is to increase the maximum array size
for the Slurm-GCP cluster.  These instructions make heavy use of Slurm's `--array` feature,
so this adjustment is recommended.  In order for it to take effect, you will need to log
into the **controller node** for the cluster and run the following command, **after** 
performing the actions above:

```bash
$ sudo systemctl restart slurmctld
```

## Set-up for a data set

Two input files are required to perform analysis across a DFI data set: a [**config file**](Format_aConfig.md)
and a [**video file-of-files**](Format_vFof.md).

The [**config file**](Format_aConfig.md) contains information about the source data and where the output
data will be written.  A template for this file is provided as `aConfig_sample.py`,
which should be copied and modified.

The [**video file-of-files**](Format_vFof.md) lists all of the video files that will go into the analysis.  This is
a text file, with each line specifying the full blob name for a single video file.  It is
assumed that each of these files are ~10-minute .mp4-format videos.  This file can be constructed
using the source data specifications from the [**config file**](Format_aConfig.md), using the `catalogAllFiles.py` script:

```bash
$ python3.7 catalogAllFiles.py -a <config file> -s input -o <video file-of-files>
```

With that file in place, the shell scripts that will be submitted to Slurm-GCP can be generated 
using the python script `createRunScripts1st.py`:

```bash
$ python3.7 createRunScripts1st.py -f <video file-of-files> -c <config file>
```

That script will create three shell scripts that will be used to deploy analysis tasks to the Slurm-GCP cluster,
as described below: `run_dfi.sh`, `run_dfi_test_48f.sh`, and `run_dfi_backfill.sh`.

## Execute analyses: initial run

Analyses can be submitted to the Slurm-GCP cluster using the `run_dfi.sh` script and Slurm's `--array` flag.  
In the array, each task will correspond to a single video file: the task number will correspond to the line
number on which that file is listed in the [**file-of-files**](Format_vFof.md).  If that file had 41,567 lines, then they could
all be submitted to the cluster simultaneously using a command such as this:

```bash
$ sbatch --array=1-41567 run_dfi.sh
```

A **test run** option is also provided.  The `run_dfi_test_48f.sh` script will launch a task in which only 
the first 48 frames of the video file will be analyzed.  This will finish quickly (should take just a few
minutes) and will produce abbreviated versions of all of the output files, along with slurm log files
(found in the `slurmlogs` directory) to help with trouble-shooting.  It is recommended to run a few of these
prior to initiating the full analysis:

```bash
$ sbatch --array=1-5 run_dfi_test_48f.sh
```

Don't forget to **delete the output files** before you begin your full run.  These files are incomplete but
will make it appear that the tasks have completed.

**Note:** the Slurm-GCP cluster will only accept array integers up to 400,000.  
If your DFI video set contains more than 400,000 videos, then launch only the first 
400,000 using these instructions, then proceed to the **backfill** instructions below.

## Execute analyses: backfill

During the deployment of your DFI analysis, some tasks may fail to complete for unknown reasons 
(and/or you may have more tasks to complete than are allowed by the Slurm-GCP array).
In such cases, you will need to identify and re-launch non-completed tasks.  Those activities are
referred to here as "**backfill**".

The **backfill** scope will be defined by a new file, the **leftover lines** file.  This file specifies
the line numbers from the [**video file-of-files**](Format_vFof.md) that contain input video files for which output files
are missing.  The first step to generate this resource is to generate a **result file-of-files**, a catalog
of all result files that exist, for one of the result categories.  This can again be accomplished with the
`catalogAllFiles.py` script.  Your [**config file**](Format_aConfig.md) specifies the order in which analyses will run, which
implies the order in which results files will be generated.  You should therefore select the result category
that was generated *last*, as it will most-inclusively capture failed tasks in need of a re-run.  In the 
sample config file that is provided, that category is `minute`:

```bash
$ python3.7 catalogAllFiles.py -a <config file> -s minute -o <result file-of-files>
```

With your **result file-of-files** in place, you can use the `getBackfillFile.py` script to generate your
**leftover lines** file.  Note: that file ***MUST*** be named `leftover_lines.txt` in order to be found by
the bash scripts:

```bash
$ python3.7 getBackfillFile.py -a <config file> -s minute -m <video file-of-files> -r <result file-of-files> -o leftover_lines.txt
```

With your **leftover lines** file `leftover_lines.txt` in place, you can use the `run_dfi_backfill.sh` to re-run only
those tasks that previously failed to complete.  For this script, the `--array` elements will correspond
to line numbers in the `leftover_lines.txt` file, each of which corresponds to a line number in the [**video file-of-files**](Format_vFof.md)
for a video file whose required output was not generated.  Use `wc` to see how many tasks you need to run:

```bash
$ wc leftover_lines.txt
       3       3      10 leftover_lines.txt
$ sbatch --array=1-3 run_dfi_backfill.sh
```

Or, if you have over 400,000 tasks remaining, launch the first 400,000 tasks before iterating on the
**backfill** process.  After each iteration of **backfill**, return to the beginning and repeat the
process until the `leftover_lines.txt` file is empty.  Then you can move on to the [Secondary Analysis](Secondary.md).
