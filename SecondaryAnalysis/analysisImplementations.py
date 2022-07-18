import numpy as _np
import argparse
import datetime as DT

# allows me to display the options
_argList = ['wh_spins','wh_gait','wh_circ',
            'coat_q','bed_mov','bwt_dlt',
            'fl_circ']


############ ONE FRAME PER MINUTE

coat_q_columns = ['coat_q(sobel)']
def coat_q(dfDataL):
  dataL = list(map(lambda i:i[-1], dfDataL))
  frCount = _getTotalFrameCount(dataL)
  if frCount==0: return 'N/A'
  else: return _getOverallMean(dataL,_getSobelList)

bed_mov_columns = ['bed_mov(pxls)']
def bed_mov(dfDataL):
  dataL = list(map(lambda i:i[-1], dfDataL))
  frCount = _getTotalFrameCount(dataL)
  if frCount==0: return 'N/A'
  else: return _getBedMeanDisp(dfDataL)

bwt_dlt_columns = ['bwt_dlt(g/day)']
def bwt_dlt(dfDataL):
  dataL = list(map(lambda i:i[-1], dfDataL))
  frCount = _getTotalFrameCount(dataL)
  if frCount<2: return 'N/A'
  else: return _getBodyWeightChange(dfDataL)

color_columns = ['color(8-bit)']
def color(dfDataL):
  dataL = list(map(lambda i:i[-1], dfDataL))
  frCount = _getTotalFrameCount(dataL)
  if frCount==0: return 'N/A'
  else: return _getOverallMean(dataL,_getColorList)

############ WHEEL

wh_spins_columns = ['spins/day']
def wh_spins(dfDataL):
  totTime,totSwitch = 0.0,0
  for dt,fps,a in dfDataL:
    nFrame,nSwitch = _getSwitchCount(a)
    totTime += nFrame / float(fps)
    totSwitch += nSwitch
  if totTime <= 0: return 'N/A'
  # normalize to the number of frames actually
  # collected for the day
  secPerDay = 60.0 * 60 * 24
  return 0.5 * totSwitch * secPerDay / totTime

# averaged across days, weighted by
# observation time on each day
wh_gait_columns = ['hertz']
def wh_gait(dfDataL):
  # organize by day
  dayToDfDataL = {}
  for dt,fps,a in dfDataL:
    day = DT.date(year=dt.year,month=dt.month,day=dt.day)
    if not(day in dayToDfDataL): dayToDfDataL[day] = []
    dayToDfDataL[day].append( (dt,fps,a) )
  # collect per-day results
  hzL,wgtL = [],[]
  for day in dayToDfDataL.keys():
    hz,wgt = _medSpinRate(dayToDfDataL[day])
    hzL.append(hz)
    wgtL.append(wgt)
  if sum(wgtL)<=0: return 'N/A'
  else: return _np.average(hzL,weights=wgtL)

wh_circ_columns = ['circ.wh']
def wh_circ(dfDataL):
  dtToActivity = {}
  for dt,fps,a in dfDataL:
    nFrame,nSwitch = _getSwitchCount(a)
    time = nFrame / float(fps)
    if time > 0:
      value = nSwitch / time
      dtToActivity[dt] = (value,time)
  return _maxTwelveDist(dtToActivity)


############ FRAME POSITIONS

fl_circ_columns = ['circ.fl']
def fl_circ(dfDataL):
  dtToActivity = {}
  for dt,fps,a in dfDataL:
    nFrame,dist = _getPosDistance(a,fps,15)
    time = nFrame / float(fps)
    if time > 0:
      value = dist / time
      dtToActivity[dt] = (value,time)
  return _maxTwelveDist(dtToActivity)


# averaged across days, weighted by
# observation time on each day
fl_gait_columns = ['kpix/sec']
def fl_gait(dfDataL):
  # organize by day
  dayToDfDataL = {}
  for dt,fps,a in dfDataL:
    day = DT.date(year=dt.year,month=dt.month,day=dt.day)
    if not(day in dayToDfDataL): dayToDfDataL[day] = []
    dayToDfDataL[day].append( (dt,fps,a) )
  # collect per-day results
  gaitL,wgtL = [],[]
  for day in dayToDfDataL.keys():
    gait,wgt = _timePerKpixForManyVid(dfDataL,15)
    gaitL.append(gait)
    wgtL.append(wgt)
  if sum(wgtL)<=0: return 'N/A'
  else: return _np.average(gaitL,weights=wgtL)

  
# RETURNS: rate (median time per kpix in sec),
#          weight (number of observed seconds)
def _timePerKpixForManyVid(dfDataL,avgN):
  if len(dfDataL)==0: return 0.0,0.0
  totalWgt = 0.0
  secDistL = []
  # ignore across-video times (like for wheel)
  for dt,fps,a in dfDataL:
    xyAvgA = _getXyAvgA(a,avgN)
    distA = _getXyDistA(xyAvgA)
    totalWgt += distA.shape[0] / fps
    # correct for off-integer FPS's
    roundErr = fps / int(fps)
    for n in range(int(fps),len(distA),int(fps)):
      secDist = _np.sum(distA[n:n+int(fps)])
      if secDist > 0:
        secDistL.append(secDist * roundErr)
  secDistA = _np.array(secDistL)
  avgSpeed = _np.average(secDistA,weights=secDistA)
  avgSpeed /= 1000 # kilo-pixels are the unit
  return avgSpeed,totalWgt


##### HELPER FUNCTIONS #####

# data is an array of (xPos,yPos,conf) rows
# RETURNS frame intervals and distance travelled (pix)
def _getPosDistance(data,fps,avgN):
  dLen = data.shape[0]
  if dLen < avgN + 1: return 0,0.0
  # generate average positions  
  xyAvgA = _getXyAvgA(data,avgN)
  # generate the distances
  distA = _getXyDistA(xyAvgA)
  return _np.sum(distA),distA.shape[0]

def _getXyDistA(xyAvgA):
  if xyAvgA.shape[0] < 2: return _np.array([])
  xDistA = xyAvgA[1:,0] - xyAvgA[:-1,0]
  yDistA = xyAvgA[1:,1] - xyAvgA[:-1,1]
  xSqA = xDistA * xDistA
  ySqA = yDistA * yDistA
  distA = _np.sqrt(xSqA + ySqA)
  return distA

def _getXyAvgA(data,avgN):
  dLen = data.shape[0]
  if dLen < avgN: return _np.zeros( (0,2) )
  xySumA = _np.zeros( (dLen-avgN+1,2) )
  for n in range(avgN):
    xySumA += data[n:dLen+n-avgN+1,:2]
  xyAvgA = xySumA / avgN
  return xyAvgA

def _medSpinRate(dfDataL):
  spinL,wgt = [],0
  for dt,fps,a in dfDataL:
    frToSec = lambda fr: fr / fps
    locSpinL = _getSpinTimes(a)
    spinL.extend(list(map(frToSec,locSpinL)))
    wgt += a.shape[0]
  if len(spinL)==0: return 0.0,0
  else:
    hz = 1.0 / _np.median(spinL)
    return hz,wgt

# finds the maximum difference between
# phased 12h blocks
# ASSUMES all data >= 0
# INPUT values are tuples: datum, weight
def _maxTwelveDist(dtToDatumWgt):
  if len(dtToDatumWgt)==0: return 'N/A'
  # organize by 24h-cycle
  startDtime = min(dtToDatumWgt.keys())
  todToDataL,todToWgtL = {},{}
  fullDataL,fullWgtL = [],[]
  for dt in dtToDatumWgt.keys():
    # ignore 'days' so these are all 24h-cycle
    tod = (dt - startDtime).seconds
    datum,wgt = dtToDatumWgt[dt]
    if tod in todToDataL:
      todToDataL[tod].append(datum)
      todToWgtL[tod].append(wgt)
    else:
      todToDataL[tod] = [datum]
      todToWgtL[tod] = [wgt]
    fullDataL.append(datum)
    fullWgtL.append(wgt)
  # now cycle through all 10-min shift possibilities;
  # i only need to go through 12 hours because I'm just
  # looking for the absolute value of difference
  diffL = []
  secIn12h = 12 * 60 * 60
  secIn10m = 10 * 60
  for startT in range(0,secIn12h,secIn10m):
    endT = startT + secIn12h
    inKL = list(filter(lambda t: t >= startT and t < endT, todToDataL.keys()))
    outKL = list(filter(lambda t: t < startT or t >= endT, todToDataL.keys()))
    if len(inKL) > 0 and len(outKL) > 0:
      inValL,outValL = [],[]
      inWgtL,outWgtL = [],[]
      for k in inKL:
        inValL.extend(todToDataL[k])
        inWgtL.extend(todToWgtL[k])
      for k in outKL:
        outValL.extend(todToDataL[k])
        outWgtL.extend(todToWgtL[k])
      if sum(inWgtL) > 0 and sum(outWgtL) > 0:
        inAvg = _np.average(inValL,weights=inWgtL)
        outAvg = _np.average(outValL,weights=outWgtL)
        diffL.append(abs(inAvg-outAvg))
  if len(diffL)==0: return 'N/A'
  else:
    meanValue = _np.average(fullDataL,weights=fullWgtL)
    return 0.5 * max(diffL) / meanValue


def _getSwitchCount(a):
  nFrame = a.shape[0]
  if nFrame < 2: return 0, 0.0
  # bottom/top are 0/1, so subtracting
  # each element from the previous will
  # produce either 1 or -1 whenever there
  # is a change, 0 whenever there isn't
  aChange = a[1:,0] - a[:nFrame-1,0]
  nChange = _np.sum(_np.absolute(aChange))
  return nFrame,nChange

def _findNextChange(a,n):
  nFrame = a.shape[0]
  if n < nFrame:
    state = a[n][0]
    while n < nFrame and a[n][0]==state: n += 1
  return n

def _getSpinTimes(a):
  nFrame = a.shape[0]
  spinL = []
  startN = _findNextChange(a,0)
  while startN < nFrame:
    midN = _findNextChange(a,startN)
    endN = _findNextChange(a,midN)
    if endN < nFrame: spinL.append(endN - startN)
    startN = endN
  return spinL  


def _getTotalFrameCount(dataL):
  return sum(list(map(_getFrameCount,dataL)))

def _getFullList(dataL,listFunct):
  if len(dataL)==0: return []
  valL = listFunct(dataL[0])
  for n in range(1,len(dataL)):
    valL.extend( listFunct(dataL[n]) )
  return valL

# assumes each row in each np.array is 1 minute;
# returns values in units of days
def _getFullTimeList(dfDataL):
  if len(dfDataL)==0: return []
  timeL = []
  minToDay = 1.0 / (24 * 60)  
  dateZero,extraA,extraB = min(dfDataL)
  for dtime,fps,dataA in dfDataL:
    dayXval = _getTimedeltaDays(dtime-dateZero)
    for n in range(dataA.shape[0]):
      timeL.append( n*minToDay + dayXval )
  return timeL

def _getOverallMean(dataL,listFunct):
  valL = _getFullList(dataL,listFunct)
  valL = list(filter(lambda i: not(_np.isnan(i)), valL))
  return _np.mean(valL)

def _getTimedeltaDays(td):
  secToDay = 1.0 / (24 * 60 * 60)  
  return float(td.days) + (td.seconds * secToDay)

def _getBodyWeightChange(dfDataL):
  regr = WeightedRegressor()
  dataL = list(map(lambda i:i[-1], dfDataL))
  # data lists
  timeL = _getFullTimeList(dfDataL)
  bwL = _getFullList(dataL,_getBodyWtList)
  cfL = _getFullList(dataL,_getBwtConfList)
  for n in range(len(timeL)):
    regr.addXY(timeL[n],bwL[n],cfL[n])
  if regr.sumW() <= 0: return 'N/A'
  return regr.slope()

# assuming that each array in dataL
# represents a 10-min video, and that the
# videos are in-order and ~continuous.
# calculating displacement as on
# nb163 p90 (getDisp), in pixels
def _getBedMeanDisp(dfDataL):
  dfDataL = list(filter(lambda i: _getFrameCount(i[-1]) > 0, dfDataL))
  if len(dfDataL) < 2: return 0
  # get the x,y coordinates for each 10-min vid segment
  dataL = list(map(lambda i:i[-1], dfDataL))
  xyL = list(map(_getBedXyPerVid,dataL))
  # get the time value for each 10-min vid segment
  dateZero,extraA,extraB = min(dfDataL)
  dtimeL = list(map(lambda i:i[0], dfDataL))
  getTenMinN = lambda dt: _getTimedeltaDays(dt-dateZero) * 24 * 6
  tenMinNL = list(map(getTenMinN, dtimeL))
  # now get the displacements
  dispL = []
  for n in range(1,len(xyL)):
    xA,yA = xyL[n-1]
    xB,yB = xyL[n]
    pixDisp = _np.sqrt( (xA-xB)**2 + (yA-yB)**2 )
    timeDisp = tenMinNL[n] - tenMinNL[n-1]
    dispL.append(pixDisp / timeDisp)
  return _np.mean(dispL)


_getFrameCount = lambda a: a.shape[0]
_getSobelList = lambda a: list(a[:,1])
_getBodyWtList = lambda a: list(a[:,2])
_getBwtConfList = lambda a: list(a[:,3])
def _getBedXyPerVid(a):
  xMn = _np.mean(a[:,4])
  yMn = _np.mean(a[:,5])
  return (xMn,yMn)
_getColorList = lambda a: list(a[:,6])



class WeightedRegressor:
  def __init__(self):
    self._sumW = 0.0
    self._sumWX = 0.0
    self._sumWY = 0.0
    self._sumWX2 = 0.0
    self._sumWY2 = 0.0
    self._sumWXY = 0.0
  def addXY(self,x,y,w):
    self._sumW += w
    self._sumWX += (w * x)
    self._sumWY += (w * y)
    self._sumWX2 += (w * x * x)
    self._sumWY2 += (w * y * y)
    self._sumWXY += (w * x * y)
  def slope(self):
    numer = (self._sumW * self._sumWXY) - (self._sumWX * self._sumWY)
    denom = (self._sumW * self._sumWX2) - (self._sumWX * self._sumWX)
    return numer / denom
  def yIntercept(self):
    diff = self._sumWY - (self._sumWX * self._slope())
    return diff / self._sumW
  def sumW(self): return self._sumW
  def meanX(self): return self._sumWX / self._sumW
  def meanY(self): return self._sumWY / self._sumW



def main():
  ap = argparse.ArgumentParser()
  for a in _argList:
    ap.add_argument("--"+a, help=a+" is an option")
  args = vars(ap.parse_args())


if __name__ == "__main__": main()
