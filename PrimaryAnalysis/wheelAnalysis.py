# hack solution to an openMP error (???) that I started getting:
# https://github.com/dmlc/xgboost/issues/1715
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

import argparse
import numpy as np
import os, sys, math, cv2
import mlModelApplyers as MMA
from google.cloud import storage
from shutil import copyfile

# A CONSTANT THAT WILL BE CHANGED FOR EACH DATASET
# PROCESSED: FALSE MEANS LEAVE THE PATHS AS THEY ARE,
# TRUE MEANS THERE ARE REDUNDANT DIRECTORIES FOR ONE 
# STUDY, SO THE TOP-LEVEL DIRECTORY WILL BE REMOVED
DoRedunantRedux = True

# THESE METHODS ARE OVER-ENGINEERED FOR THIS TASK
# This script is designed to perform the wheel-spin
# analysis across a specific data set, as costrained
# by the methods below. For other data sets, this
# script should be copied and the functions below
# modified.
def getInputComponents(input_mov_full):
    # get the components of the path: bucket & blob name
    input_mov_bucket = input_mov_full[5:].split('/')[0]
    # remove the leading 'gs', bucket name, and trailing slash
    input_mov_blob = input_mov_full[5 + len(input_mov_bucket) + 1:]
    if input_mov_bucket != "calico-vium-local-rack1":
        raise ValueError('bad bucket: '+input_mov_bucket)
    # NOTE: this data set has no folder within the bucket: the
    # paths go straight from bucket->device_id
    input_mov_project = "vium-data"
    return input_mov_project, input_mov_bucket, input_mov_blob
def getOutputComponents(input_mov_full):
    out_project = "graham-video-ai-202006"
    out_bucket = "graham-calico-video-analysis-results-a1"
    out_folder = "wheel-spin-exp-696/EXP-696-ALL"
    in_proj,in_buck,in_blob = getInputComponents(input_mov_full)
    # NOTE: for this data set, the input blob has no
    # folder within the bucket (starts with device_id)
    if in_blob[-4:]!='.mp4':
        raise ValueError("input file should be .mp4 format")
    out_path = in_blob[:-4] + '.npy'
    # REDUNDANCY REDUCTION: STRIP FIRST DIRECTORY
    if DoRedunantRedux:
      out_path = '/'.join(out_path.split('/')[1:])
    out_blob = os.path.join(out_folder,out_path)
    return out_project, out_bucket, out_blob

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input_mp4",
                    help="the video file, full path in google cloud storage")
    ap.add_argument("-n","--max_frames",
                    help="the max number of frames to analyze (default: full vid)",
                    default="-1")
    ap.add_argument("-t","--tmp_dir",
                    help="the path to the temp dir (could be 'scratch'?)",
                    default="/tmp")
    # for benchmarking
    args = vars(ap.parse_args())

    # ignore max frames if it wasn't specified (or nonsense)
    max_frames = int(args["max_frames"])
    # -1 is allowed to indicate ALL frames
    if max_frames < -1:
        raise ValueError("max frames cannot be negative")
    use_max_frames = (max_frames >= 0)

    input_mov_full = args["input_mp4"]
    if input_mov_full.find('gs://')!=0:
        raise ValueError("mp4 file path doesn't look like Google cloud")

    # necessary info for reading & writing data to/from cloud
    in_mov_project,in_mov_bucket,in_mov_blob = getInputComponents(input_mov_full)
    out_npy_project,out_npy_bucket,out_npy_blob = getOutputComponents(input_mov_full)

    # to prevent collisions by jobs running on the same machine
    # (this might not be a problem for VM clusters?)
    loc_file_id = np.random.randint(100000000)
    input_mov_local = os.path.join(args["tmp_dir"],"local_input_"+str(loc_file_id)+".mp4")
    output_npy_local = os.path.join(args["tmp_dir"],"local_output_"+str(loc_file_id)+".npy")

    print('FILE TRANSFER IN')
    storage_client_in = storage.Client(project=in_mov_project)
    bucket_in = storage_client_in.bucket(in_mov_bucket)
    blob_in = bucket_in.blob(in_mov_blob)
    blob_in.download_to_filename(input_mov_local)
    print('done.')
    
    wheelMod,markerMod,stateMod = getThreeModels()
    stateToNum = {'bottom':0.0, 'top':1.0}
    stateL = ['bottom','top']
    print('PROCESSING VIDEO')
    if use_max_frames:
        processVideoToNpy(input_mov_local,output_npy_local,stateL,stateToNum,
                          wheelMod=wheelMod,markerMod=markerMod,stateMod=stateMod,
                          initPD=initPD_WW,trMatrix=trMatrix_WW,
                          maxFr=max_frames )
    else:
        processVideoToNpy(input_mov_local,output_npy_local,stateL,stateToNum,
                          wheelMod=wheelMod,markerMod=markerMod,stateMod=stateMod,
                          initPD=initPD_WW,trMatrix=trMatrix_WW)
    print('done.')

    print('FILE TRANSFER OUT')
    storage_client_out = storage.Client(project=out_npy_project)
    bucket_out = storage_client_out.bucket(out_npy_bucket)
    blob_out = bucket_out.blob(out_npy_blob)
    blob_out.upload_from_filename(output_npy_local)
    print('done.')
    
    # Clean up
    print('CLEANING /TMP')
    os.remove(input_mov_local)
    os.remove(output_npy_local)
    print('done.')

    
def processVideoToNpy(inputFile, outputFile, labelL, stateToNum,
                      wheelMod=None, markerMod=None, stateMod=None,
                      initPD=None, trMatrix=None,
                      maxFr=-1):
    if wheelMod==None or markerMod==None or stateMod==None:
        raise ValueError("missing model")
    # constants for mask-image drawing
    imgConstD = {'maskV':255,'wCh':0,'mCh':1}
    # initialize the output file
    if outputFile==None: raise ValueError('output file needed (.npy)')
    for lab in labelL:
        if not(lab in stateToNum): raise ValueError('missing key: '+lab)
    # parse frames
    stateL = collectStatesHelp(inputFile,stateMod,wheelMod,markerMod,imgConstD,maxFr)
    traceL = hmmActivitiesHelp(stateL,initPD,trMatrix)
    # create the output array
    dataOut = np.ndarray( (len(traceL),3), dtype=float)
    labToIndex = {}
    for n in range(len(labelL)): labToIndex[labelL[n]] = n + 1
    for n in range(len(traceL)):
        dataOut[n][0] = stateToNum[traceL[n]]
        for lab in labelL:
            dataOut[n][labToIndex[lab]] = stateL[n].score(lab)
    np.save(outputFile,dataOut)


def getMaskImgHelp(inImg,wheelMod,markerMod,imgConstD):
    maskV,wCh,mCh = map(lambda i: imgConstD[i], ['maskV','wCh','mCh'])
    h,w = inImg.shape[:2]
    ho2,wo2 = int(h/2),int(w/2)
    trImg = inImg[0:ho2, wo2:w, :]
    wMask = wheelMod.getMask(trImg)
    mMask = markerMod.getMask(trImg)
    wMask *= maskV
    mMask *= maskV
    outImg = np.zeros(inImg.shape)
    outImg[0:ho2,wo2:w,wCh] = wMask
    outImg[0:ho2,wo2:w,mCh] = mMask
    return outImg

def collectStatesHelp(inputFile,stateMod,wheelMod,markerMod,imgConstD,maxF=-1):
    cap = cv2.VideoCapture(inputFile)
    if not( cap.isOpened()): raise ValueError("not opened")
    speedFps = cap.get(cv2.CAP_PROP_FPS)
    imgOk,imgFrame = cap.read()
    imgH,imgW = imgFrame.shape[:2]
    stateL = []
    while imgOk and maxF!=0:
        maxF -= 1
        maskImg = getMaskImgHelp(imgFrame,wheelMod,markerMod,imgConstD)
        stateL.append( stateMod.getClasses(maskImg) )
        imgOk,imgFrame = cap.read()
    cap.release()
    return stateL

# applies the Viterbi algorithm to the activity classifications
def hmmActivitiesHelp(stateL,initPD,trMatrix):
    lpL,tbL = [initPD],[None] # log-probabilities & tracebacks
    for n in range(len(stateL)):
        aco = stateL[n]
        if aco==None: raise ValueError("aco should not be none: frame "+str(n))
        lpD,tbD = {},{}
        for sNow in trMatrix.keys():
            emP = math.log(aco.score(sNow))
            trOpL = [(trMatrix[s][sNow] + lpL[-1][s], s) for s in trMatrix.keys()]
            p,s = max(trOpL)
            lpD[sNow] = p + emP
            tbD[sNow] = s
        lpL.append(lpD)
        tbL.append(tbD)
    finOpL = [(lpL[-1][s],s) for s in lpL[-1].keys()]
    fP,fS = max(finOpL)
    traceL,pos = [fS],len(lpL)-1
    while pos > 1:
        traceL.append(tbL[pos][traceL[-1]])
        pos -= 1
    traceL.reverse()
    if len(traceL)!= len(stateL):
        raise ValueError("length error in hmm traceback")
    return traceL




# for args that will be used semi-permanently
perms = {}
perms["w_pos_label"] = 'ML_models/wheel_class_train_b.labels.txt'
perms["w_pos_model"] = 'ML_models/wheel_class_int_10000.pb'

perms["w_mask_model"] = 'ML_models/wheel_mask_wheelface.54'
perms["w_mask_model_type"] = "vgg_unet"
perms["w_mask_n_classes"] = "2"
perms["w_mask_input_height"] = "96"
perms["w_mask_input_width"] = "128"
perms["w_mask_output_height"] = "48"
perms["w_mask_output_width"] = "64"

perms["m_mask_model"] = 'ML_models/wheel_mask_marker.17'
perms["m_mask_model_type"] = "vgg_unet"
perms["m_mask_n_classes"] = "2"
perms["m_mask_input_height"] = "96"
perms["m_mask_input_width"] = "128"
perms["m_mask_output_height"] = "48"
perms["m_mask_output_width"] = "64"

# initial probabilities (diff for water/wheel)
# see nb146 p168
initPD_WW = {'top': 0.325, 'bottom': 0.675}
# I'm using my own bias to calculate probabilities for transitioning
# out of each state, then applying the remaining initial probabilities.
# FOR NOW: my bias is that it should stay in the state for 3 frames
trMatrix_WW = {}
for sA in initPD_WW.keys():
    trMatrix_WW[sA] = {}
    restSum = sum(initPD_WW.values()) - initPD_WW[sA]
    for sB in initPD_WW.keys():
        if sB == sA: trMatrix_WW[sA][sB] = 2.0/3
        else: trMatrix_WW[sA][sB] = initPD_WW[sB] / (restSum * 3)
# make these into log values
for k in initPD_WW.keys(): initPD_WW[k] = math.log(initPD_WW[k])
for k in trMatrix_WW.keys():
    for k2 in trMatrix_WW[k].keys():
        trMatrix_WW[k][k2] = math.log(trMatrix_WW[k][k2])

def getThreeModels():
    print('LOADING MODELS')
    wheelMod = MMA.KrSegModelApplyer(perms["w_mask_model_type"],
                                 int(perms["w_mask_n_classes"]),
                                 int(perms["w_mask_input_width"]),
                                 int(perms["w_mask_input_height"]),
                                 perms["w_mask_model"])
    markerMod = MMA.KrSegModelApplyer(perms["m_mask_model_type"],
                                 int(perms["m_mask_n_classes"]),
                                 int(perms["m_mask_input_width"]),
                                 int(perms["m_mask_input_height"]),
                                 perms["m_mask_model"])
    stateMod = MMA.TfClassifier(perms["w_pos_model"],perms["w_pos_label"])
    print('done.')
    return wheelMod,markerMod,stateMod


if __name__ == "__main__": main()
