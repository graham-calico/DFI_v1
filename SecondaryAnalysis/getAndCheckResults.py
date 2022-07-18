import datetime as DT
import argparse
import os
import numpy as np
import subprocess
from google.cloud import storage

def main():  
  ap = argparse.ArgumentParser()
  ap.add_argument("-i","--id_list_file",
                  help="the file listing mouse ID's for this study, one per line")
  ap.add_argument("-o","--output_dir",
                  help="local directory where by-mouse output files are written")
  ap.add_argument("-g","--gcloud_output_dir",
                  help="Allows jobs to be run on the cluster: outfiles temp written to this GCloud 'directory' (starts w/gs://)")
  ap.add_argument("--just_check",
                  help="don't transfer any cloud files, just see what's missing locally",
                  action='store_true')
  args = vars(ap.parse_args())

  usingGcloud = (args["gcloud_output_dir"] is not None)
  doingTransfer = (usingGcloud and not args["just_check"])

  # get the mouse IDs as a list
  f = open(args["id_list_file"])
  idList = list(map(lambda i: i.strip(), f.readlines()))
  f.close()

  # see what's already there
  idsPreDone = getPresentIds(idList,args['output_dir'])
  
  # retrieve files from the cloud
  if doingTransfer:
    idsToGet = list(filter(lambda i: i not in idsPreDone, idList))
    for i in idsToGet:
      idfName = i+'.tsv'
      gcSource = os.path.join(args['gcloud_output_dir'],idfName)
      localTarg = os.path.join(args['output_dir'],idfName)
      transferFileFromCloud(gcSource,localTarg)
  
  # see what's there now
  idsAllDone = getPresentIds(idList,args['output_dir'])

  # figure out what's done, what's left over
  numTot = len(idList)
  numDone = len(idsAllDone)
  numNew = numDone - len(idsPreDone)
  numNeed = numTot - numDone
  print(str(numNew)+" new results collected from the cloud.")
  print(str(numDone)+" results out of "+str(numTot)+" are complete.")
  print(str(numNeed)+" results are still needed.")

  if numNeed > 0:
    needNL = list(filter(lambda n: idList[n] not in idsAllDone, range(len(idList))))
    # since slurm --array calls (line numbers) are 1-indexed:
    needNL = list(map(lambda n: n+1, needNL))
    # a list of 2-item lists, each representing a range of #'s
    needAL = [ [needNL[0],needNL[0]] ]
    if len(needNL) > 1:
      for nn in needNL[1:]:
        if nn == needAL[-1][1] + 1:
          needAL[-1][1] = nn
        else: needAL.append( [nn,nn] )
    # convert into text, for slurm --array
    needTL = []
    for nA,nB in needAL:
      if nA==nB: needTL.append(str(nA))
      else: needTL.append(str(nA)+'-'+str(nB))
    needTT = ','.join(needTL)
    print("The following task numbers need to be run: "+needTT)

# allows other ids to be present in the same dir
def getPresentIds(idList,in_dir):
  idD_sought = {}
  for i in idList: idD_sought[i] = None
  idD_found = {}
  infileL = os.listdir(in_dir)
  infileL = list(filter(lambda i: len(i)>4 and i[-4:]=='.tsv', infileL))
  for infname in infileL:
      mouseId = infname[:-4]
      if mouseId in idD_sought:
        idD_found[mouseId] = None
  return idD_found


def transferFileFromCloud(gcFile,localFile):
    # if using GCloud, copy the results file to the cloud
    # then delete the local copy (gsutil mv does both)
    gsCommand = ("gsutil mv "+gcFile+" "+localFile).split()
    p = subprocess.Popen(gsCommand)
    (output,err) = p.communicate()
    


if __name__ == "__main__": main()

