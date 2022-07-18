<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# DFI: Secondary Analysis

This page provides instructions for the Secondary Analysis phase of digital frailty: 
the derivation of quantitative phenotypes from results of per-video analyses.
In a "map-reduce" framework, this corresponds to a "reduce" function: it will consolidate
numerical results from the outputs of analyses of each video file, which
were performed in the [**Primary Analysis**](Primary.md) step.

This system is designed to operate on video files stored in Google Cloud buckets. **MORE HERE**

## Installation: Slurm-GCP or a single GCP VM

This analysis can be performed on the same Slurm-GCP cluster on which the
[**Primary Analysis**](Primary.md) was performed.  Individual tasks can be
run locally on the login node or submitted to the cluster.  The installation
instructions for the [**Primary Analysis**](Primary.md) step also provide all
of necessary components for this step.


## Set-up for a data set

**WARNING:** make sure that the [**Primary Analysis**](Primary.md) is completely
finished before initiating the **Secondary Analysis**.  Also, make sure that
the **python3.7** module has been loaded:

```bash
$ module load python/3.7.8
```

Navigate to the `SecondaryAnalysis` directory, and use `createRunScripts2nd.py`
to generate all of the files and scripts that you will need a [**config file**](Format_aConfig.md) 
(also used in the [**Primary Analysis**](Primary.md)) and a [**device ID map file**](Format_DevMap.md),
which defines where data for individual mice are stored, and across which blocks of time (each block
of time corresponds to a measurement of Digital Frailty).

Phenotype values will initially be calculated on a per-animal basis.  Create a local directory in which
the results of those analyses can be stored, then run `createRunScripts2nd.py` to generate all of the
resources required to execute the analyses:

```bash
$ mkdir <result directory>
$ python3.7 createRunScripts2nd.py -c <config file> -d <device ID map file> -g <cloud result dir> -o <result directory>
```

The `<cloud result dir>` specifies a directory path in a Google Cloud bucket for which you have write access.
This will be used as a temporary write destination for tasks that are submitted to the SlurmGCP cluster.
It should be a unique path for this analysis, but the files written to it will not persist there once the analysis
is complete (they will be transferred to the local `<result directory>`).  This should be the full path, starting
with `gs://` followed by the bucket name.  It will be accessed using `gsutil` by the scripts below.  If it is
not specified, scripts will still be generated for running these analyses locally (*not recommended for large studies*).

If you plan on performing multiple analyses on this cluster using different config and device ID map files, 
you can generate resources (shell scripts that you will run below) that are labelled specifically for
each analysis using the `-l <unique label>` flag.  The default value is `dfi`; if you invoke this flag, then
your uniqe label will appear in place of `dfi` in the names of all shell scripts and support files listed below.

**MORE HERE:** [OUTPUT FILE LIST & BRIEF DESCRIPTION]


## Execute analyses: phenptype values

For each of the phenotypes evaluated for Digital Frailty, values are compiled from the video-analysis results
from the [**Primary Analysis**](Primary.md), spanning across all of the DFI measurement time blocks defined
in the [**device ID map file**](Format_DevMap.md) for a single animal.  The index of the argument provided
to `runLocal_dfi.sh` or the Slurm task number provided to the script from integers provided to Slurm's `--array`
argument will indicate the line number of the [**ID list file**](Format_idList.md) containing the ID of the
animal to be analyzed:

```bash
$ sbatch --array=1-20 runSlurm_dfi.sh
```

It is recommended that you use the Slurm cluster to parallelize these tasks, using the `runSlurm` version
of the run script, as specified above.  You can copy the output files to the local directory and verify
the completion of all tasks using the `getAndCheckResults.py` script:

```bash
$ python3.7 getAndCheckResults.py -i <id list file> -o <result directory> -g <cloud result dir>
```

This script will report on which result files are missing (which line numbers from the 
[**ID list file**](Format_idList.md) do not have corresponding result files in the **result directory**).
If there are a small number of tasks that need to be run - perhaps due to a Slurm failure - then that 
can be accomplished by either submitting new jobs to the cluster as described above, or by running each
remaining task individually using the `runLocal` version of the run script:

```bash
$ ./runLocal_dfi.sh 1
```

Once the `getAndCheckResults.py` script reports that there are no remaining tasks to be run, you can
move on to the **DFI parameterization** step below.

## Execute analyses: DFI parameterization

The final step of the Digital Frailty pipeline is to parameterize phenotype values and calculate
the final frailty scores.  This step will also consolidate all of the results from your study into
a single `.tsv` file, with a row for each mouse/measurement instance (labelled with the mouse's ID
and the date on which the observations for that measurement began).  This is accomplished using the
`dfiValuesToScores.py` script, providing the **result directory** from above as the input and specifying
a **final results file** to which the output will be written:

```bash
$ python3.7 dfiValuesToScores.py -i <result directory> -o <final results file>
```

An alternative version of this script (`dfiValuesToValues.py`) is provided that consolidates and
outputs the raw phenotype values, prior to frailty parameterization.  These values are similar but
not identical to the phenotype values found in the **result directory**.  Those phenotypes include
coat color, which is not a frailty phenotype but is used to adjust the Sobel gradient-based "coat quality"
measure.  Coat color will not be included in this output file, and the "coat quality" value will have been
adjusted:

```bash
$ python3.7 dfiValuesToValues.py -i <result directory> -o <final phenotypes file>
```

