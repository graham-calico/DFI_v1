<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# File Format: ID list file

This file is auto-generated during the [**Secondary Analysis**](Secondary.md) step, by the script `createRunScripts2nd.py`.  
It contains a non-redundant list of animal ID's from the [**device ID map file**](Format_DevMap.md) that was provided to that
script as an argument to the `-d` flag.  It's name will be `idList_dfi.txt`, with the `dfi` portion optionally modified by
the `-l` flag input to the `createRunScripts2nd.py` script.

Animal ID's will be listed one-per-line, separated by newlines.  The line numbers will be used by the `runLocal_dfi.sh` 
and `runSlurm_dfi.sh` scripts (and their `_test` equivalents).  The integers provided to those scripts (either directly 
as an argument to the `runLocal` version, or as a Slurm task number deriving from the `--array` argument to the `runSlurm`
version) will specify the line from this file on which the animal ID for the given task can be found.  For a data set,
the scope of tasks that need to be run is defined by the number of lines in this file:

```bash
$ wc idList_dfi.txt
       3       3      18 idList_dfi.txt
$ sbatch --array=1-3 runSlurm_dfi.sh
```
