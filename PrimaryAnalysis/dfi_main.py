# hack solution to an openMP error (???) that I started getting:
# https://github.com/dmlc/xgboost/issues/1715
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

# references to local analytical files
CANDIDATE_ANALYSES = {}
CANDIDATE_ANALYSES['wheel'] = 'wheelAnalysis_mod.py'
CANDIDATE_ANALYSES['box'] = 'boxPos_mod.py'
CANDIDATE_ANALYSES['minute'] = 'eachMin_HrWtBd_mod.py'

import argparse
import numpy as np
import os, sys, math, cv2
import tensorflow as tf
from google.cloud import storage
from shutil import copyfile

# generates a function with project/bucket built in
def makeGetBlobStrFunc(input_mov_project,input_mov_bucket):
  # REQUIRES: this is a google cloud storage object
  # in the above-specified bucket
  def getBlobString(input_mov_full):
    splitPath = input_mov_full.split(input_mov_bucket)
    if len(splitPath) < 2:
        sys.stderr.write('movie: '+input_mov_full+'\n')
        sys.stderr.write('bucket: '+input_mov_bucket+'\n')
        raise ValueError('specified movie is not from specified bucket')
    # assume the first instance of the bucket name is the bucket
    # itself: this allows for sub-dirs to have the same name as
    # the bucket, though that is not advised.
    in_blob = input_mov_bucket.join(splitPath[1:])
    if len(in_blob)==0:
        raise ValueError('movie file had nothing beyond bucket')
    if in_blob[0]=='/':
        if len(in_blob)==1:
            raise ValueError('movie file had nothing beyond bucket')
        in_blob = in_blob[1:]
    return in_blob
  return getBlobString

def analysisImporter(pythonScript):
  d = {}
  f = open(pythonScript)
  exec(f.read(),d,d)
  f.close()
  return d



def main():
    # load up all of the candidate ML analyses
    candAnalysisD = {}
    for ca in CANDIDATE_ANALYSES.keys():
        candAnalysisD[ca] = analysisImporter(CANDIDATE_ANALYSES[ca])

    ap = argparse.ArgumentParser(conflict_handler='resolve')
    ap.add_argument("-a","--analysis_config",
                    help="a file specifying which analyses to be run & where to write (outD_X vars)")
    ap.add_argument("-i","--input_mp4",
                    help="the video file, full path in google cloud storage")
    ap.add_argument("-t","--tmp_dir",
                    help="the path to the temp dir (could be 'scratch'?)",
                    default="/tmp")
    for analysis in candAnalysisD.values(): analysis['addArgs'](ap)
    args = vars(ap.parse_args())

    # make sure analyses are co-compliant (match up
    # with existing analyses and not writing to the
    # same target paths)
    analysisConfig = analysisImporter(args['analysis_config'])
    alCnfEr = 'analysis_config: '

    # get the input project/bucket info
    input_mov_project = analysisConfig['input_mov_project']
    input_mov_bucket = analysisConfig['input_mov_bucket']
    getBlobString = makeGetBlobStrFunc(input_mov_project,input_mov_bucket)

    # get the analyses
    if len(analysisConfig['aInfoL'])==0:
      raise ValueError(alCnfEr+'config file specifies no analyses (aInfoL var)')
    alreadyAdded = []
    for aiD_a in analysisConfig['aInfoL']:
        if not(aiD_a['name'] in CANDIDATE_ANALYSES):
          raise ValueError(alCnfEr+'no analyisis matching label: '+aiD_a['name'])
        for aiD_b in alreadyAdded:
          if aiD_a['name'] == aiD_b['name']:
            raise ValueError(alCnfEr+'two entries found for: '+aiD_a['name'])
          aiMatchA = (aiD_a['out_project'] == aiD_b['out_project'])
          aiMatchB = (aiD_a['out_bucket'] == aiD_b['out_bucket'])
          aiMatchC = (aiD_a['out_folder'] == aiD_b['out_folder'])
          if aiMatchA and aiMatchB and aiMatchC:
            raise ValueError(alCnfEr+'two entries writing to same place: '+aiD_a['name']+', '+aiD_b['name'])
        alreadyAdded.append(aiD_a)
    analysisL = []
    for aInfD in analysisConfig['aInfoL']:
        analysisObj = candAnalysisD[aInfD['name']]
        analysisObj['specifyOutput'](aInfD)
        analysisL.append(analysisObj)
        
    input_mov_full = args["input_mp4"]
    if input_mov_full.find('gs://')!=0:
        raise ValueError("mp4 file path doesn't look like Google cloud")

    # necessary info for reading & writing data to/from cloud
    in_mov_project,in_mov_bucket = input_mov_project,input_mov_bucket 
    in_mov_blob = getBlobString(input_mov_full)

    # to prevent collisions by jobs running on the same machine
    # (this might not be a problem for VM clusters?)
    loc_file_id = np.random.randint(100000000)
    input_mov_local = os.path.join(args["tmp_dir"],"local_input_"+str(loc_file_id)+".mp4")

    print('FILE TRANSFER IN')
    storage_client_in = storage.Client(project=in_mov_project)
    bucket_in = storage_client_in.bucket(in_mov_bucket)
    blob_in = bucket_in.blob(in_mov_blob)
    blob_in.download_to_filename(input_mov_local)
    print('done.')

    # a legacy variable, no longer meaningful                                                                                     
    # but must exist                                                                                                              
    DoRedundantRedux = True
    
    for analysis in analysisL:
      output_local = analysis['output_file_local'](args["tmp_dir"],loc_file_id)
      analysis['runLocalAnalysis'](input_mov_local,output_local,args)
      analysis['moveOutputToCloud'](input_mov_full,in_mov_bucket,output_local,DoRedundantRedux)
      print('local clean')
      os.remove(output_local)

    # Clean up
    print('CLEANING /TMP')
    os.remove(input_mov_local)
    print('done.')


if __name__ == "__main__": main()
