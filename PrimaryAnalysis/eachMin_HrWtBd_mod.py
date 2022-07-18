# this script is a separate implementation of the programmatic
# interface for the wheel-spin analysis.  In future, I'll build
# this directly into the script.
import hairTexture as HAIR
import weightEst as BWT
import bedMasker as BED
from google.cloud import storage
import os, cv2, numpy as np

# function-specific args
def addArgs(ap):
  pass

globalOutputInfo = {}
def specifyOutput(outInfoD):
  for reqK in ['out_project','out_bucket','out_folder']:
    globalOutputInfo[reqK] = outInfoD[reqK]

def output_file_local(temp_dir,loc_file_id):
  return os.path.join(temp_dir,"wheel_output_"+str(loc_file_id)+".npy")

def moveOutputToCloud(input_mov_full,input_mov_bucket,local_output,doRedRedux):
  out_project,out_bucket,out_blob = _getOutputComponents(input_mov_full,input_mov_bucket,doRedRedux)
  # this needs to happen twice, once for each file
  print('FILE TRANSFER OUT')
  storage_client_out = storage.Client(project=out_project)
  bucket_out = storage_client_out.bucket(out_bucket)
  blob_out = bucket_out.blob(out_blob)
  blob_out.upload_from_filename(local_output)
  print('done.')

# output will be .npy format
# args: none to specify
def runLocalAnalysis(input_mov_local,output_npy_local,args):
  # the frequency with which to analyze frames
  secondsPerSnap = 60

  # the resources for running prediction
  weightPredM = BWT.makeWeightPredictor()
  sobelEstM = HAIR.makeSobelEstimator()
  bedPosF = BED.getMeanPosFunction()

  print('PROCESSING BWT AND HAIR')
  
  # iterate through images of video
  cap = cv2.VideoCapture(input_mov_local)
  if not( cap.isOpened()): raise ValueError("not opened")
  speedFps = cap.get(cv2.CAP_PROP_FPS)
  framesPerMin = int(speedFps * secondsPerSnap)
  imgOk = cap.grab()
  imgN,resultL = 0,[]
  while imgOk:
    if imgN % framesPerMin == 0:
      imgOk,usedImg = cap.retrieve()
      sobel,lightness = sobelEstM.mouseSobel(usedImg)
      bodyWt,bwConf = weightPredM.predictWeight(usedImg)
      # these are each (mean,percentile) tuples
      bedXmp,bedYmp = bedPosF(usedImg)
      # just the mean positions
      bedX,bedY = bedXmp[0],bedYmp[0]
      resultL.append( [imgN,sobel,bodyWt,bwConf,bedX,bedY,lightness] )
    imgN += 1
    imgOk = cap.grab()

  if len(resultL)==0: resShape = (0,0)
  else: resShape = (len(resultL),len(resultL[0]))
  resultA = np.ndarray( resShape, dtype=float)
  for nA in range(len(resultL)):
    for nB in range(len(resultL[nA])):
      resultA[nA][nB] = resultL[nA][nB]
  np.save(output_npy_local,resultA)
  print('done.')

  

def _getOutputComponents(input_mov_full,input_mov_bucket,doRedundantRedux):
  if len(globalOutputInfo)==0:
    raise ValueError('output components were not provided')
  out_project = globalOutputInfo['out_project']
  out_bucket = globalOutputInfo['out_bucket']
  out_folder = globalOutputInfo['out_folder']
  # remove the leading 'gs', bucket name, and trailing slash
  in_blob = input_mov_full[5 + len(input_mov_bucket) + 1:]
  # NOTE: for this data set, the input blob has no
  # folder within the bucket (starts with device_id)
  if in_blob[-4:]!='.mp4':
    raise ValueError("input file should be .mp4 format")
  out_path = in_blob[:-4] + '.npy'
  # REDUNDANCY REDUCTION: STRIP FIRST DIRECTORY
  if doRedundantRedux:
    out_path = '/'.join(out_path.split('/')[1:])
  out_blob = os.path.join(out_folder,out_path)
  return out_project, out_bucket, out_blob

