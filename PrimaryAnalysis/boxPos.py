import os, cv2, sys
import argparse, os, numpy as np
import mlModelApplyers as MMA


def getBestBox(boxL):
  if len(boxL)==0: return None
  boxL = list(map(lambda n: (boxL[n].score(),n,boxL[n]), range(len(boxL))))
  bestSc,trashN,bestBox = max(boxL)
  return bestBox


class MouseDetector:
  def __init__(self,mouseDet):
    self._mDetM = mouseDet
  def findMouse(self,inImg):
    # find the mouse (box)
    boxL = self._mDetM.getBoxes(inImg)
    bestBox = getBestBox(boxL)
    boxExpVal = self._mDetM.getBoxExpandVal()
    bestBox.adjustSize(boxExpVal,inImg)
    bb = bestBox
    return bb.xCenter(),bb.yCenter(),bb.score()

perms = {}
perms['mBox'] = {}
perms['mBox']['file'] = "ML_models/mouseDet_ig200127.pb"
perms['mBox']['label'] = "ML_models/mouseDet_label.pbtxt"
  

def makeMouseDetector():
  objDetMod = MMA.TfObjectIdentifier(perms['mBox']['file'],perms['mBox']['label'])
  mouseDetM = MouseDetector(objDetMod)
  return mouseDetM

def main():
  md = makeMouseDetector()
  print('worked')
    

if __name__ == "__main__": main()
