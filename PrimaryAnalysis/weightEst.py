import os, cv2, sys
import argparse, os, numpy as np
import mlModelApplyers as MMA

# see nb155 p69 for the origins of this math
class LensGeometry:
  def __init__(self,f_value):
    self._fVal = f_value
    self._yxDimToNormA = {}
  def getPixSize(self,yxDim):
    if not(yxDim in self._yxDimToNormA):
      self._yxDimToNormA[yxDim] = self._makeNormArray(yxDim)
    return self._yxDimToNormA[yxDim]
  def _makeNormArray(self,yxDim):
    yxDimA = np.array(yxDim)
    # initially, each pixel has a pixel area of 1,
    # which allows me to skip the square-root part
    # areaA = np.zeros(yxDim) + 1
    # widEqA = np.sqrt(areaA)
    # the two lines above are consolidated into one:
    widEqA = np.zeros(yxDim) + 1
    yxMid = yxDimA / 2.0
    # +0.5 ensures no zero-value coords (center of pixel)
    yxEqA = np.indices(yxDim) + 0.5
    for n in [0,1]: yxEqA[n,:,:] -= yxMid[n]
    angA = np.arctan2(yxEqA[0,:,:],yxEqA[1,:,:])
    rEqA = np.sqrt(yxEqA[0,:,:]**2 + yxEqA[1,:,:]**2)
    # versus my prior effort, I can skip d_eq since
    # i'm not using the whole mask, just the pixel
    rRecA = self._fVal * np.tan(rEqA / self._fVal)
    widRecA = widEqA * rRecA / rEqA
    return widRecA**2
    

def getBestBox(boxL):
  if len(boxL)==0: return None
  boxL = list(map(lambda n: (boxL[n].score(),n,boxL[n]), range(len(boxL))))
  bestSc,trashN,bestBox = max(boxL)
  return bestBox

  

class ImageDirLister:
  def __init__(self,hostDir,append='.png'):
    # check that the host dir exists
    if not(os.path.isdir(hostDir)):
      raise ValueError("host dir doesn't exist")
    self._hostD = os.path.abspath(hostDir)
    self._append = append
  def getImgFiles(self):
    imgFL = os.listdir(self._hostD)
    imgFL.sort()
    aLen = len(self._append)
    imgFL = list(filter(lambda i: i[-aLen:]==self._append, imgFL))
    imgFL = list(map(lambda i: os.path.join(self._hostD,i), imgFL))
    return imgFL
class ImageFileLister:
  def __init__(self,fileOfFiles):
    # check that the host dir exists
    if not(os.path.isfile(fileOfFiles)):
      raise ValueError("file-of-files doesn't exist")
    self._fofName = fileOfFiles
  def getImgFiles(self):
    f = open(self._fofName)
    imgFL = f.readlines()
    f.close()
    imgFL = list(map(lambda i: i.rstrip(), imgFL))
    return imgFL
  
class ImageDirScorer:
  def __init__(self,weightMod,fileLister):
    self._scorer = weightMod
    self._fileLister = fileLister
    self._colL = ['File','Weight','Conf']
  def scoreImages(self,outfileName):
    imgFL = self._fileLister.getImgFiles()
    print("Analyzing "+str(len(imgFL))+" images.")
    if outfileName=='stdout':
      outf = sys.stdout
      progress = NullDotWriter()
    else:
      outf = open(outfileName,'w')
      progress = DotWriter(5,50,250)
    outf.write('\t'.join(self._colL)+'\n')
    outf.flush()
    count = 0
    for imgF in imgFL:
      progress.tick()
      img = cv2.imread(imgF)
      wt,conf = self._scorer.predictWeight(img)
      resL = [imgF,str(wt),str(conf)]
      outf.write('\t'.join(resL) + '\n')
      outf.flush()
    if outf!=sys.stdout: outf.close()


class DotWriter:
  def __init__(self,perDot,perBar,perLine):
    self._pDot = perDot
    self._pBar = perBar
    self._pLine = perLine
    self._count = 0
  def tick(self):
    self._count += 1
    if self._count % self._pBar == 0: sys.stdout.write('|')
    elif self._count % self._pDot == 0: sys.stdout.write('.')
    if self._count % self._pLine == 0: sys.stdout.write('\n')
    sys.stdout.flush()
class NullDotWriter:
  def __init__(self): pass
  def tick(self): pass

      





class WeightPredictor:
  def __init__(self,mouseDet,mouseMsk,isMouseCls,lensGeo,pixVolToWgt):
    self._mDetM = mouseDet
    self._mMskM = mouseMsk
    self._isMsClM = isMouseCls
    self._adjType = 'none'
    self._pixVolToWgt = pixVolToWgt
    # resource for adjusting fish-eye properties
    self._lensGeo = LensGeometry(lensGeo)
  # two methods for setting the adjustment (default=none)
  def setAdjustFilter(self,adjustCls,okClass):
    self._adjType = 'filter'
    self._adjClM = adjustCls
    self._noAdjClass = okClass
  def setAdjustment(self,adjustCls,classToMultiD):
    self._adjType = 'adjust'
    self._adjClM = adjustCls
    self._adjMultiD = classToMultiD
  def predictWeight(self,inImg):
    # find the mouse (box)
    boxL = self._mDetM.getBoxes(inImg)
    bestBox = getBestBox(boxL)
    boxExpVal = self._mDetM.getBoxExpandVal()
    bestBox.adjustSize(boxExpVal,inImg)
    bb = bestBox
    # get the mask (using box sub-img)
    subImg = inImg[bb.yMin():bb.yMax(),bb.xMin():bb.xMax(),:]
    subMask = self._mMskM.getMask(subImg)
    fullMask = np.zeros(inImg.shape[:2])
    fullMask[bb.yMin():bb.yMax(),bb.xMin():bb.xMax()] = subMask
    # adjust the pixel values of the mask according
    # to the lens distortion equations
    lensAdjA = self._lensGeo.getPixSize(fullMask.shape)
    lensMask = fullMask * lensAdjA
    # get preliminary estimate
    lensArea = np.sum(lensMask)
    lensVol = np.sqrt(lensArea)**3
    # get a version of the image for classification
    greySlice = np.mean(inImg,axis=2)
    clsImg = np.copy(inImg)
    clsImg[:,:,0] = fullMask * 255
    for n in [1,2]: clsImg[:,:,n] = greySlice
    # get the weight/is-it-a-mouse
    isMsRes = self._isMsClM.getClasses(clsImg)
    if isMsRes.best()=='mouse':
      estWeight = 2 * (isMsRes.score('mouse') - 0.5)
    else: estWeight = 0.0
    # get & use the adjustment value
    if self._adjType!='none' and estWeight > 0:
      adjRes = self._adjClM.getClasses(clsImg)
      if self._adjType=='filter':
        if self._noAdjClass!=adjRes.best(): estWeight = 0.0
      elif self._adjType=='adjust':
        lensVol *= self._adjMultiD[adjRes.best()]
      else:
        raise ValueError('bad option for adjustment type: '+adjType)
    return lensVol * self._pixVolToWgt, estWeight

perms = {}
perms['pixWt'] = {}
perms['pixWt']['pxVolToWt'] = 37.55455694434747 / 2868253.0712112184
perms['pixWt']['lensGeo'] = 415.0
perms['mSeg'] = {}
perms['mSeg']['file'] = "ML_models/mouse_mask_mouse.164"
perms['mSeg']['type'] = "vgg_unet"
perms['mSeg']['inW'] = 256
perms['mSeg']['inH'] = 256
perms['mSeg']['clN'] = 2
perms['mBox'] = {}
perms['mBox']['file'] = "ML_models/mouseDet_ig200127.pb"
perms['mBox']['label'] = "ML_models/mouseDet_label.pbtxt"
perms['mBox']['expand'] = 1.2
perms['isM'] = {}
perms['isM']['file'] = "ML_models/isMouse_int_6000.pb"
perms['isM']['label'] = "ML_models/isMouse_labels.txt"
perms['adj'] = {}
perms['adj']['file'] = "ML_models/weightAdj_int_7000.pb"
perms['adj']['label'] = "ML_models/weightAdj_labels.txt"
perms['adj']['okClass'] = 'b'
perms['adj']['multi'] = {}
perms['adj']['multi']['a'] = 1.0 / 0.46
perms['adj']['multi']['b'] = 1.0
perms['adj']['multi']['c'] = 1.0 / 2.5
  

def makeWeightPredictor():
  segMod = MMA.KrSegModelApplyer(perms['mSeg']['type'],perms['mSeg']['clN'],
                                 perms['mSeg']['inW'],perms['mSeg']['inH'],
                                 perms['mSeg']['file'])
  objDetMod = MMA.TfObjectIdentifier(perms['mBox']['file'],perms['mBox']['label'],
                                     perms['mBox']['expand'])
  
  isMouseMod = MMA.TfClassifier(perms['isM']['file'],perms['isM']['label'])
  weightPredM = WeightPredictor(objDetMod,segMod,isMouseMod,
                                perms['pixWt']['lensGeo'],perms['pixWt']['pxVolToWt'])
  adjustMod = MMA.TfClassifier(perms['adj']['file'],perms['adj']['label'])
  weightPredM.setAdjustment(adjustMod,perms['adj']['multi'])
  return weightPredM

def main():
  # start the app
  ap = argparse.ArgumentParser()
  ap.add_argument("-i","--input_dir",
                  help="input directory of images to be scored (or .txt file listing images)")
  ap.add_argument("-o","--output_file",
                  help="output file of box locations")
  ap.add_argument("-a","--img_append",
                  help="the file append for images (only needed if -i is a directory)",
                  default='png')
  ap.add_argument("--adjust_mode",
                  help="the way to use the weight-adj model (d: none)",
                  default='none')
  args = vars(ap.parse_args())
  
  if args["adjust_mode"]!='none':
    adjustMod = MMA.TfClassifier(perms['adj']['file'],perms['adj']['label'])
    if args["adjust_mode"]=='filter': 
      weightPredM.setAdjustFilter(adjustMod,perms['adj']['okClass'])
    elif args["adjust_mode"]=='adjust': 
      weightPredM.setAdjustment(adjustMod,perms['adj']['multi'])
    else:
      optList = ['none','filter','adjust']
      raise ValueError('bad --adjust_mode option, pick from: '+str(optList))
  
  if not(args["input_dir"]): raise ValueError('need an input file/dir')
  elif os.path.isdir(args["input_dir"]):
    imgLister = ImageDirLister(args["input_dir"],args["img_append"])
  elif os.path.isfile(args["input_dir"]):
    imgLister = ImageFileLister(args["input_dir"])
  else: raise ValueError("input is nether a directory nor a file")
  
  weightPredM = makeWeightPredictor()
  imgMang = ImageDirScorer(weightPredM,imgLister)
  if args["output_file"]: outfName = args["output_file"]
  else: outfName = 'stdout'
  
  imgMang.scoreImages(outfName)
    

if __name__ == "__main__": main()
