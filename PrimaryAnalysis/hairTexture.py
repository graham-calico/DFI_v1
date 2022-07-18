import datetime as DT
import argparse, os, sys
import numpy as np, cv2
import mlModelApplyers as MMA



def makeSobelEstimator():
  # make the model applicators
  segModType = "vgg_unet"
  nClass,inW,inH = 2,256,256
  segModFile = "ML_models/mouse_mask_mouse.164"
  segModel = MMA.KrSegModelApplyer(segModType,nClass,inW,inH,segModFile)

  objDetModFile = "ML_models/mouseDet_ig200127.pb"
  objDetCatFile = "ML_models/mouseDet_label.pbtxt"
  objDetModel = MMA.TfObjectIdentifier(objDetModFile,objDetCatFile)
  boxExpandValue = 1.2

  return SobelEstimator(objDetModel,boxExpandValue,segModel)
  

class SobelEstimator:
  def __init__(self,objDetModel,boxExpandValue,segModel):
    self._objM = objDetModel
    self._boxExpV = boxExpandValue
    self._segM = segModel
  def mouseBox(self,inImg):
    return getBestObjDetBox(inImg,self._objM)
  def mouseSobel(self,inImg):
    return getSobel(inImg,self._objM,self._boxExpV,self._segM)

  
def getBestObjDetBox(inImg,objDetModel):
  boxL = objDetModel.getBoxes(inImg)
  if len(boxL)==0: return None
#  boxL = list(map(lambda i: (i.score(),i), boxL))
#  bestSc,bestBox = max(boxL)
  boxL = list(map(lambda n: (boxL[n].score(),n,boxL[n]), range(len(boxL))))
  bestSc,trashN,bestBox = max(boxL)
  return bestBox

def getSobel(inImg,objDetModel,boxExpandValue,segModel):
    bestBox = getBestObjDetBox(inImg,objDetModel)
    bestBox.adjustSize(boxExpandValue,inImg)
    bb = bestBox
    subImg = inImg[bb.yMin():bb.yMax(),bb.xMin():bb.xMax(),:]
    subMask = segModel.getMask(subImg)
    ### vvv NEW FOR MEASURING TEXTURE vvv ###
    gray = cv2.cvtColor(subImg, cv2.COLOR_BGR2GRAY)
    gX = cv2.Sobel(gray, cv2.CV_64F, 1, 0)
    gY = cv2.Sobel(gray, cv2.CV_64F, 0, 1)
    magnitude = np.sqrt((gX ** 2) + (gY ** 2))
    # limit it to just the mask area
    magInMask = magnitude * subMask
    meanSobel = np.sum(magInMask) / np.sum(subMask)
    ### coat lightness
    justMaskVal = np.extract(subMask!=0,gray)
    return meanSobel,np.median(justMaskVal)

def main():  
  ap = argparse.ArgumentParser()
  ap.add_argument("-i","--img_dir",
                  help="directory of image files, named N.jpg where N is the line number from -w")
  ap.add_argument("-c","--color_dir",
                  help="dir for output images (input images with colored masks, same name)")
  ap.add_argument("-o","--out_file",
                  help="each line contains result for a file")
  ap.add_argument("-a","--in_append",
                  help="append for input files")
  ap.add_argument("-p","--print_results",
                  help="also print outfile results to stdout",
                  action='store_true')                  
  args = vars(ap.parse_args())

  # input img dir & files
  if not(os.path.isdir(args["img_dir"])):
    raise ValueError('input img dir not found')
  inAppend = args["in_append"]
  hasAppend = lambda i: len(i)>len(inAppend) and i[-len(inAppend):]==inAppend
  infileList = os.listdir(args["img_dir"])
  infileList = list(filter(hasAppend, infileList))
  infileList = list(map(lambda i: os.path.join(args["img_dir"],i), infileList))
  
  # output are optional
  writeColorImgs = False
  if args["color_dir"]:
    writeColorImgs = True
    if not(os.path.isdir(args["color_dir"])):
      raise ValueError('output colored img dir not found')
    makeOutImgFname = getImgFileMaker(args["color_dir"])
  writeStdOut = args["print_results"]

  writeOutputVals = False
  if args["out_file"]:
    writeOutputVals = True
    if os.path.isfile(args["out_file"]):
      raise ValueError('outfile exists, would have been over-written')

  if not(writeOutputVals) and not(writeColorImgs) and not(writeStdOut):
    raise ValueError("you're not doing anything with the output")

  sobelEstM = makeSobelEstimator()

  # TO DO: open output files
  if writeOutputVals:
    outf = open(args["out_file"],'w')
  
  # run the analysis  
  for n in range(len(infileList)):
    if not(writeStdOut):
      if n % 10 == 0:
        sys.stdout.write('.')
        if n % 500 == 0: sys.stdout.write('\n')
        sys.stdout.flush()
    inName = infileList[n]
    if writeStdOut:
      sys.stdout.write( os.path.basename(inName) + '\t')
      sys.stdout.flush()
      
    inImg = cv2.imread(inName)
    meanSobel,lightness = sobelEstM.mouseSobel(inImg)

    if writeOutputVals:
      dataL = [os.path.basename(inName),meanSobel,lightness]
      outf.write('\t'.join(list(map(str,dataL))) + '\n')

    if writeStdOut:
      print((meanSobel,lightness))
    
    if writeColorImgs:
      greySlice = np.mean(inImg,axis=2)
      outImg = np.copy(inImg)
      outImg[:,:,0] = fullMask * 255
      outImg[:,:,1] = greySlice
      outImg[:,:,2] = greySlice
      cv2.imwrite(makeOutImgFname(n),outImg)
  
  if writeOutputVals: outf.close()

  print('Done.')
    
if __name__ == "__main__": main()

