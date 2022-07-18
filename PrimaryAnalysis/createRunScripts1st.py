# generates shell scripts that can be submitted to Slurm-GCP
# using --array 

import argparse, os, sys, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c","--config_file",
                    help="REQ: the config file for these analyses (copy of aConfig_sample.py)")
    ap.add_argument("-f","--file_of_files",
                    help="REQ: file listing all video files in GCloud")
    ap.add_argument("-l","--custom_label",
                    help="OPT: special name label for scripts & tasks (def: dfi)",
                    default="dfi")
    ap.add_argument("--sbatch_nodes",
                    help="OPT: sbatch --nodes arg (def: 1)",
                    default="1")
    ap.add_argument("--sbatch_cpus",
                    help="OPT: sbatch --cpus-per-task arg (def: 4)",
                    default="4")
    args = vars(ap.parse_args())

    if not(os.path.isfile(args['config_file'])):
      raise ValueError('config file not found: '+args['config_file'])
    if not(os.path.isfile(args['file_of_files'])):
      raise ValueError('file-of-vid-files not found: '+args['file_of_files'])

    # update the basic, universal version of the script
    findReplaceL = []
    findReplaceL.append( ('[CONFIG FILE NAME HERE]',args['config_file']) )
    findReplaceL.append( ('[FILE OF FILES NAME HERE]',args['file_of_files']) )
    findReplaceL.append( ('[SBATCH NODES HERE]',args['sbatch_nodes']) )
    findReplaceL.append( ('[SBATCH CPUS HERE]',args['sbatch_cpus']) )
#    findReplaceL.append( ('',args['']) )
    
    baseScript = runFullInitial
    for oldTxt,newTxt in findReplaceL:
      baseScript = changeMarker(baseScript,oldTxt,newTxt)

    # make the three output files
    mustChangeL = []
    mustChangeL.append('[ASSIGN FILE NUMBER HERE]')
    mustChangeL.append('[ASSIGN JOB NAME HERE]')
    mustChangeL.append('[EXTRA ARGS HERE]')
#    mustChangeL.append('')

    chgD_full = {}
    chgD_full['fname'] = 'run_'+args['custom_label']+'.sh'
    chgD_full['[EXTRA ARGS HERE]'] = ''
    chgD_full['[ASSIGN JOB NAME HERE]'] = args['custom_label']+'A'
    chgD_full['[ASSIGN FILE NUMBER HERE]'] = assign_fnum_normal
#    chgD_full[''] = ''
    
    chgD_backf = {}
    chgD_backf['fname'] = 'run_'+args['custom_label']+'_backfill.sh'
    chgD_backf['[EXTRA ARGS HERE]'] = ''
    chgD_backf['[ASSIGN JOB NAME HERE]'] = args['custom_label']+'B'
    chgD_backf['[ASSIGN FILE NUMBER HERE]'] = assign_fnum_backfill
#    chgD_backf[''] = ''
    
    chgD_test = {}
    chgD_test['fname'] = 'run_'+args['custom_label']+'_test_48f.sh'
    chgD_test['[EXTRA ARGS HERE]'] = '" -n 48"'
    chgD_test['[ASSIGN JOB NAME HERE]'] = args['custom_label']+'T'
    chgD_test['[ASSIGN FILE NUMBER HERE]'] = assign_fnum_normal
#    chgD_test[''] = ''

    # now create the three scripts (only if they don't exist)
    chgDL = [chgD_full,chgD_backf,chgD_test]
    for chgD in chgDL:
      if os.path.isfile(chgD['fname']):
        raise ValueError('shell script already exists: '+chgD['fname'])
    for chgD in chgDL:
      localScript = baseScript
      for chgTxt in mustChangeL:
        localScript = changeMarker(localScript,chgTxt,chgD[chgTxt])
      fout = open(chgD['fname'],'w')
      fout.write(localScript)
      fout.close()
      locScrStat = os.stat(chgD['fname'])
      os.chmod(chgD['fname'], locScrStat.st_mode | stat.S_IEXEC)

# helper for swapping out text elements, includes
# tests to make sure each element exists exactly once
def changeMarker(fullScript,oldTxt,newTxt):
  if fullScript.find(oldTxt)==-1:
    raise ValueError('old text missing: "'+oldTxt+'"')
  splitScriptL = fullScript.split(oldTxt)
  if len(splitScriptL)!=2:
    raise ValueError('old text found >once: "'+oldTxt+'"')
  return newTxt.join(splitScriptL)

      
# two ways to assign the file number (regular or backfill)
assign_fnum_normal = "FILENUM=$TASKNUM"
assign_fnum_backfill = """NUMFILE="leftover_lines.txt"
FILENUM=`head -n ${TASKNUM} ${NUMFILE} | tail -n 1`"""

runFullInitial = """#!/bin/bash
#SBATCH --job-name=[ASSIGN JOB NAME HERE]
#SBATCH --nodes=[SBATCH NODES HERE]
#SBATCH --cpus-per-task=[SBATCH CPUS HERE]
#SBATCH --output=slurmlogs/job_%A_%a.txt

TASKNUM=$SLURM_ARRAY_TASK_ID
echo "Task num is: " $TASKNUM

[ASSIGN FILE NUMBER HERE]
echo "File num is: " $FILENUM

module load python/3.7.8
SOURCEFILE="[FILE OF FILES NAME HERE]"
INFILE=`head -n ${FILENUM} ${SOURCEFILE} | tail -n 1`

TASK="python3.7 dfi_main.py -a [CONFIG FILE NAME HERE] -i "${INFILE}[EXTRA ARGS HERE]
echo ${TASK}
${TASK}
echo "Done."
"""



if __name__ == "__main__": main()

