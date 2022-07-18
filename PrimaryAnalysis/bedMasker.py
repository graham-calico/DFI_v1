# hack solution to an openMP error (???) that I started getting:
# https://github.com/dmlc/xgboost/issues/1715
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

import argparse
import numpy as np
import os, sys, math, cv2
from google.cloud import storage
from shutil import copyfile
import mlModelApplyers as MMA

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
    out_folder = "BeddingAnalysis/AgeStudy210409"
#    out_folder = "wheel-spin-exp-696/EXP-696-ALL"
    in_proj,in_buck,in_blob = getInputComponents(input_mov_full)
    # NOTE: for this data set, the input blob has no
    # folder within the bucket (starts with device_id)
    if in_blob[-4:]!='.mp4':
        raise ValueError("input file should be .mp4 format")
    out_path = in_blob[:-4] + '.png'
    # REDUNDANCY REDUCTION: STRIP FIRST DIRECTORY
    if DoRedunantRedux:
      out_path = '/'.join(out_path.split('/')[1:])
    out_blob = os.path.join(out_folder,out_path)
    return out_project, out_bucket, out_blob

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input_mp4",
                    help="the video file, full path in google cloud storage")
    ap.add_argument("-t","--tmp_dir",
                    help="the path to the temp dir (could be 'scratch'?)",
                    default="/tmp")
    args = vars(ap.parse_args())

    input_mov_full = args["input_mp4"]
    if input_mov_full.find('gs://')!=0:
        raise ValueError("mp4 file path doesn't look like Google cloud")

    # necessary info for reading & writing data to/from cloud
    in_mov_project,in_mov_bucket,in_mov_blob = getInputComponents(input_mov_full)
    out_png_project,out_png_bucket,out_png_blob = getOutputComponents(input_mov_full)

    # to prevent collisions by jobs running on the same machine
    # (this might not be a problem for VM clusters?)
    loc_file_id = np.random.randint(100000000)
    input_mov_local = os.path.join(args["tmp_dir"],"local_input_"+str(loc_file_id)+".mp4")
    output_png_local = os.path.join(args["tmp_dir"],"local_output_"+str(loc_file_id)+".png")

    print('FILE TRANSFER IN')
    storage_client_in = storage.Client(project=in_mov_project)
    bucket_in = storage_client_in.bucket(in_mov_bucket)
    blob_in = bucket_in.blob(in_mov_blob)
    blob_in.download_to_filename(input_mov_local)
    print('done.')
    
    bedMod = getModel()
    print('PROCESSING VIDEO')
    processVideoToPng(input_mov_local,output_png_local,bedMod=bedMod)
    print('done.')

    print('FILE TRANSFER OUT')
    storage_client_out = storage.Client(project=out_png_project)
    bucket_out = storage_client_out.bucket(out_png_bucket)
    blob_out = bucket_out.blob(out_png_blob)
    blob_out.upload_from_filename(output_png_local)
    print('done.')
    
    # Clean up
    print('CLEANING /TMP')
    os.remove(input_mov_local)
    os.remove(output_png_local)
    print('done.')

    
def processVideoToPng(inputFile, outputFile, bedMod=None):
    if bedMod==None: raise ValueError("missing model")
    # initialize the output file
    if outputFile==None: raise ValueError('output file needed (.png)')
    # apply model to get output image
    wentOk,outImg = makeMaskImgHelp(inputFile,bedMod)
    # write the output file
    if wentOk:
      cv2.imwrite(outputFile,outImg)
    else:
      print('problem reading the movie file, no frame extracted')

def getMeanPosFunction():
  bedMod = getModel()
  chanl = getBedChannel()
  def meanPosFunct(img):
    mask = bedMod.getMask(img)
    xPos = getAxisMeanStd(mask,chanl,'x')
    yPos = getAxisMeanStd(mask,chanl,'y')
    return (xPos,yPos)
  return meanPosFunct


# originally written for "trialAnalysis_210412.py";
# see nb163 p88 for use of output
def getAxisMeanStd(mask,chanl,axisName):
  # the axis is the one for the percentiles,
  # so I need to summ along the OTHER axis.
  if axisName.lower()=='x': saxN = 0
  elif axisName.lower()=='y': saxN = 1
  else: raise ValueError('bad axis name: '+axisName)
  chanA = np.where(mask==chanl,1,0)
  histA = np.sum(mask,saxN)
  # multiply the counts by their positions
  # for calculating the mean position
  posA = np.array(range(histA.shape[0]))
  posSum = np.sum(posA * histA)
  countSum = np.sum(histA)
  meanPos = posSum / countSum
  # calculating SD
  resA = posA - meanPos
  resSqA = resA * resA
  resSqSum = np.sum(resSqA * histA)
  sdPos = np.sqrt( resSqSum / countSum )
  # add 0.5 to the mean pos due to
  # center-of-pixel issue
  return meanPos + 0.5, sdPos

# returns an image-shaped array where the
# 0th color is the mask (either 0 or 255)
# and the 1st & 2nd colors are a b&w version
# of the input image.  That will allow me to
# clearly visualize the mask in the context
# of the original image.  I may want to change
# this later.
def getMaskImgHelp(inImg,bedMod):
    bMask = bedMod.getMask(inImg)
    # the blank structure for writing the out image
    outImg = np.zeros(inImg.shape)
    # create a b&w version of the image for the 1&2 channels (g&r)
    bwSlice = np.mean(inImg,axis=2)
    outImg[:,:,1] = bwSlice
    outImg[:,:,2] = bwSlice
    # set the mask to the 0th color (bgr, so blue)
    outImg[:,:,0] = bMask * 255
    return outImg

def makeMaskImgHelp(inputFile,bedMod):
    cap = cv2.VideoCapture(inputFile)
    if not( cap.isOpened()): raise ValueError("not opened")
    speedFps = cap.get(cv2.CAP_PROP_FPS)
    # only analyze the first frame
    imgOk,imgFrame = cap.read()
    if imgOk: maskImg = getMaskImgHelp(imgFrame,bedMod)
    else: maskImg = None
    cap.release()
    return imgOk,maskImg


# for args that will be used semi-permanently
perms = {}
perms["b_mask_model"] = 'ML_models/bed_mask_bedB.10'
perms["b_mask_model_type"] = "vgg_unet"
perms["b_mask_n_classes"] = "2"
perms["b_mask_input_height"] = "512"
perms["b_mask_input_width"] = "768"
perms["b_mask_bed_channel"] = "1"

def getModel():
    print('LOADING MODELS')
    bedMod = MMA.KrSegModelApplyer(perms["b_mask_model_type"],
                                   int(perms["b_mask_n_classes"]),
                                   int(perms["b_mask_input_width"]),
                                   int(perms["b_mask_input_height"]),
                                   perms["b_mask_model"])
    print('done.')
    return bedMod

def getBedChannel():
    return int(perms["b_mask_bed_channel"])

if __name__ == "__main__": main()
