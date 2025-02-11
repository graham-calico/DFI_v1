# generates shell scripts that can be submitted to Slurm-GCP
# using --array 

import argparse, os, sys, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c","--config_file",
                    help="REQ: the config file for these analyses (copy of aConfig_sample.py)")
    ap.add_argument("-d","--dev_map_file",
                    help="REQ: device & ID mapping file (see documentation)")
    ap.add_argument("-o","--output_dir",
                    help="REQ: directory int which output files will be written")
    ap.add_argument("-g","--gcloud_output_dir",
                    help="Outfiles temp written to this GCloud dir (starts w/gs://).",
                    default='')
    ap.add_argument("--slurm",
                    help="sets it run on slurm",
                    action="store_true")
    ap.add_argument("-s","--source_mount",
                    help="source files found on this mounted bucket path (alt to bucket name)",
                    default='')
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

    # will scripts be created allowing cluster running,
    # i.e. writing output to gcloud?
    usingGcloud = args["slurm"]

    # static name (will be modified with "custom_label"
    uniqueIdFile = "idList_"+args['custom_label']+".txt"

    if not(os.path.isfile(args['config_file'])):
      raise ValueError('config file not found: '+args['config_file'])
    if not(os.path.isfile(args['dev_map_file'])):
      raise ValueError('device & ID mapping file not found: '+args['dev_map_file'])
    if os.path.isfile(uniqueIdFile):
      raise ValueError('unique ID file already exists, would have been over-written')
    if len(args['output_dir'])==0 or not(os.path.isdir(args['output_dir'])):
      raise ValueError("output directory doesn't exist: "+args['output_dir'])
    # make sure that the trailing slash is present
    if not(args['output_dir'][-1]=='/'): args['output_dir'] += '/'
    # this is an option for the slurm tasks
    usingGcpOut = not(args['gcloud_output_dir']=='')
    if usingGcpOut:
      if not(args['gcloud_output_dir'][-1]=='/'):
        args['gcloud_output_dir'] += '/'

    usingBmount = not(args['source_mount']=='')
    if usingBmount:
      bucketMount = args['source_mount']
      if not(os.path.isdir(bucketMount)):
        raise ValueError('bucket mount not found')
        
    # make sure slurmlog directory exists
    slurmlogDir = 'slurmlogs'
    if usingGcloud:
      if not(os.path.isdir(slurmlogDir)):
        os.mkdir(slurmlogDir)
    
    # construct the file of unique IDs
    mouseIdD = {}
    f = open(args['dev_map_file'])
    for i in f.readlines():
        newMouseId = i.rstrip().split('\t')[4]
        mouseIdD[newMouseId] = None
    f.close()
    # delay creation of this file

    # update the basic, universal version of the script
    findReplaceL = []
    findReplaceL.append( ('[ID LIST FILE NAME HERE]',uniqueIdFile) )
    findReplaceL.append( ('[CONFIG FILE NAME HERE]',args['config_file']) )
    findReplaceL.append( ('[DEV MAP FILE NAME HERE]',args['dev_map_file']) )
    
    baseScript = runFullInitial
    for oldTxt,newTxt in findReplaceL:
      baseScript = changeMarker(baseScript,oldTxt,newTxt)

      
    chgD_local = {}
    chgD_local['fname'] = 'runLocal_'+args['custom_label']+'.sh'
    chgD_local['header'] = header_for_local
    chgD_local['[OUTPUT COMMAND HERE]'] = "-o "+args['output_dir']+"${MOUSEID}.tsv"
    chgD_local['[EXTRA ARGS HERE]'] = ''
    chgD_local['[ASSIGN TASK NUMBER HERE]'] = assign_tasknum_local
#    chgD_local[''] = ''

    chgD_testL = {}
    chgD_testL['fname'] = 'runLocal_'+args['custom_label']+'_test.sh'
    chgD_testL['header'] = header_for_local
    chgD_testL['[OUTPUT COMMAND HERE]'] = "-o "+args['output_dir']+"${MOUSEID}.tsv"
    chgD_testL['[EXTRA ARGS HERE]'] = ' --one_block_test'
    chgD_testL['[ASSIGN TASK NUMBER HERE]'] = assign_tasknum_local
#    chgD_testL[''] = ''
      
    if usingBmount:
      chgD_local['[EXTRA ARGS HERE]'] += " -l "+bucketMount
      chgD_testL['[EXTRA ARGS HERE]'] += " -l "+bucketMount
      
    if usingGcloud:
      chgD_slurm = chgD_local.copy()
      chgD_slurm['fname'] = 'runSlurm_'+args['custom_label']+'.sh'
      chgD_slurm['header'] = header_for_slurm
      if usingGcpOut:
        chgD_slurm['[OUTPUT COMMAND HERE]'] = "-g "+args['gcloud_output_dir']+"${MOUSEID}.tsv"
      chgD_slurm['[ASSIGN JOB NAME HERE]'] = args['custom_label']
      chgD_slurm['[ASSIGN TASK NUMBER HERE]'] = assign_tasknum_slurm
      chgD_slurm['[SBATCH NODES HERE]'] = args['sbatch_nodes']
      chgD_slurm['[SBATCH CPUS HERE]'] = args['sbatch_cpus']
#      chgD_slurm[''] = ''

      chgD_testS = chgD_testL.copy()
      chgD_testS['fname'] = 'runSlurm_'+args['custom_label']+'_test.sh'
      chgD_testS['header'] = header_for_slurm
      if usingGcpOut:
        chgD_testS['[OUTPUT COMMAND HERE]'] = chgD_slurm['[OUTPUT COMMAND HERE]']
      chgD_testS['[ASSIGN JOB NAME HERE]'] = args['custom_label']+'T'
      chgD_testS['[ASSIGN TASK NUMBER HERE]'] = assign_tasknum_slurm
      chgD_testS['[SBATCH NODES HERE]'] = args['sbatch_nodes']
      chgD_testS['[SBATCH CPUS HERE]'] = args['sbatch_cpus']
#      chgD_testS[''] = ''

    # now create the four scripts (2 for local, 2 for slurm)
    chgDL = [chgD_local,chgD_testL]
    if usingGcloud: chgDL.extend( [chgD_slurm,chgD_testS] )
    for chgD in chgDL:
      if os.path.isfile(chgD['fname']):
        raise ValueError('shell script already exists: '+chgD['fname'])
    for chgD in chgDL:
      localScript = baseScript
      # change the header first since it might
      # have components that need to change
      localScript = changeMarker(localScript,'[ASSIGN HEADER HERE]',chgD['header'])
      for chgTxt in chgD.keys():
        if chgTxt!='fname' and chgTxt!='header':
          localScript = changeMarker(localScript,chgTxt,chgD[chgTxt])
      fout = open(chgD['fname'],'w')
      fout.write(localScript)
      fout.close()
      locScrStat = os.stat(chgD['fname'])
      os.chmod(chgD['fname'], locScrStat.st_mode | stat.S_IEXEC)

    # creating the mouse ID file, specified above
    f = open(uniqueIdFile,'w')
    for i in mouseIdD.keys(): f.write(i+'\n')
    f.close()


# helper for swapping out text elements, includes
# tests to make sure each element exists exactly once
def changeMarker(fullScript,oldTxt,newTxt,allowMissing=False):
  if fullScript.find(oldTxt)==-1:
    if not(allowMissing):
      raise ValueError('old text missing: "'+oldTxt+'"')
    else: pass
  splitScriptL = fullScript.split(oldTxt)
  if len(splitScriptL)>2:
    raise ValueError('old text found >once: "'+oldTxt+'"')
  return newTxt.join(splitScriptL)


# two ways to assign the file number (regular or backfill)
assign_tasknum_local = "TASKNUM=$1"
assign_tasknum_slurm = "TASKNUM=$SLURM_ARRAY_TASK_ID"


header_for_local = "#!/bin/bash"
header_for_slurm = """#!/bin/bash
#SBATCH --job-name=[ASSIGN JOB NAME HERE]
#SBATCH --nodes=[SBATCH NODES HERE]
#SBATCH --cpus-per-task=[SBATCH CPUS HERE]
#SBATCH --output=slurmlogs/job_%A_%a.txt
"""



runFullInitial = """[ASSIGN HEADER HERE]

[ASSIGN TASK NUMBER HERE]
#echo "Task num is: " $TASKNUM

TASKFILE="[ID LIST FILE NAME HERE]"
MOUSEID=`head -n ${TASKNUM} ${TASKFILE} | tail -n 1`

#echo $MOUSEID
module load python/3.7.8

TASKA="python3.7 dfiCalculateValues.py -d [DEV MAP FILE NAME HERE]"
TASKB="-a [CONFIG FILE NAME HERE]"
TASKC="[OUTPUT COMMAND HERE]"
TASKD="-m ${MOUSEID}[EXTRA ARGS HERE]"

TASK="${TASKA} ${TASKB} ${TASKC} ${TASKD}"

echo ${TASK}
${TASK}
"""


# prior version
"""#!/bin/bash
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

TASK="python3.7 dfi_211216.py -a [CONFIG FILE NAME HERE] -i "${INFILE}[EXTRA ARGS HERE]
echo ${TASK}
${TASK}
echo "Done."
"""



if __name__ == "__main__": main()

