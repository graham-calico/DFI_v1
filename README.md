<p>
    <a href="https://docs.calicolabs.com/python-template"><img alt="docs: Calico Docs" src="https://img.shields.io/badge/docs-Calico%20Docs-28A049.svg"></a>
    <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

# MyProject

![](https://github.com/calico/myproject)

## Overview

This repository contains all code necessary to calculate Digital Frailty Index scores
from a home-cage video data set.  This is organized as a two-step process:
1. Processing of primary video data to generate numerical output;
2. Statistical processing of numerical data to produce Frailty scores.

This repository is organized according to those steps.  For the first step,
it is assumed that it will be run in a high-throughput computing (HTC) environment.
This repository was written for use with a SLURM-GCP cluster and may need adjustment
for other HTC solutions.  The second step is more flexible in terms of computing environments,
but is written assuming GCP buckets as the primary solution for storage of intermediate data.

[**Instructions for the Primary Analysis**](docs/Primary.md)

[**Instructions for the Secondary Analysis**](docs/Secondary.md)

## What You Will Need to Provide for an Analysis

- A Google Cloud bucket for which you have write access;
- A data set of videos, formatted [**as specified**](docs/Spec_vidFiles.md);
- A [**configuration file**](docs/Format_aConfig.md) for your study;
- A [**device & ID mappings**](docs/Format_DevMap.md) file for your study.

## File Formats for Resources Generated Along the Way

- A [**video file-of-files**](docs/Format_vFof.md) for your data set

## Index of Specifications

- [**Video file naming & storage reqs.**](docs/Spec_vidFiles.md)
- [**File Format: analysis config file**](docs/Format_aConfig.md)
- [**File Format: device & ID mappings**](docs/Format_DevMap.md)
- [**File Format: video file-of-files**](docs/Format_vFof.md)

## License

See LICENSE

## Maintainers

See CODEOWNERS
