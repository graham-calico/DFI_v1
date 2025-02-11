import datetime as DT
import argparse
import os
import numpy as np
import subprocess
from google.cloud import storage
import shutil, stat

CONST_FRAME_PER_SEC = 24

def main():  
  ap = argparse.ArgumentParser()
  ap.add_argument("-d","--devmap_file",
                  help="the file mapping out mouse/device/times for DFI collection periods")
  ap.add_argument("-a","--analysis_config",
                  help="a file specifying which analyses to be run & where to write (outD_X vars)")
  ap.add_argument("-m","--mouse_id",
                  help="the ID for one mouse, to be analyzed")
  ap.add_argument("-o","--out_file",
                  help="the result (output) file (also basename for temp dirs)")
  ap.add_argument("-g","--gcloud_out_file",
                  help="the result (output) file, path for gcloud writing (INSTEAD of -o)")
  ap.add_argument("-l","--local_bucket_mount",
                  help="optional: a path leading to the mounted bucket",
                  default='')
  ap.add_argument("--one_block_test",
                  help="limits analysis to one date block (~1 week)",
                  action='store_true')
  args = vars(ap.parse_args())

  usingLocalOut = (args["out_file"] is not None)
  usingGcloudOut = (args["gcloud_out_file"] is not None)
  if usingLocalOut and usingGcloudOut:
    raise ValueError("must write to only local OR gcloud")
  if not(usingLocalOut) and not(usingGcloudOut):
    raise ValueError("must write to either local OR gcloud")
  if usingGcloudOut:
    gcOutfName = args["gcloud_out_file"]
  usingLocBucket = False
  if args['local_bucket_mount']:
    usingLocBucket = True
    localBucket = args['local_bucket_mount']
    if not os.path.isdir(localBucket):
      raise ValueError('local mount path to bucket not valid')

  # all of the analyses to be performed, in the order
  # of their columns in the output file
  analysisL = ['wh_spins','wh_gait','wh_circ',
               'coat_q','bwt_dlt','bed_mov',
               'fl_circ','fl_gait','color']

  # the data analyses corresponding to each data source
  # (keys: data source, values: relevant analyses)
  dataSrcToAnalyses = {}
  dataSrcToAnalyses['wheel'] = ['wh_spins','wh_gait','wh_circ']
  dataSrcToAnalyses['minute'] = ['coat_q','bwt_dlt','bed_mov','color']
  dataSrcToAnalyses['box'] = ['fl_gait','fl_circ']
  dataSourceL = dataSrcToAnalyses.keys()
  analysisD = getFileAsDict('analysisImplementations.py')
  
  aConfigD = getFileAsDict(args['analysis_config'])
    
  gsToDataDir = {}  
  for dataName in dataSourceL:
    for analysis_type in dataSrcToAnalyses[dataName]:
      if not(analysis_type in analysisD):
        opts = filter(lambda i: i[0]!='_', analysisD)
        opts = filter(lambda i: i.find('_columns')==-1, opts)
        print("Options: " + ', '.join(opts))
        raise ValueError("analysis type not found")
      if not(analysis_type+"_columns" in analysisD):
        raise ValueError("analysis type is missing '_columns' label function")
    if usingLocBucket:
      gsToDataDir[dataName] = makeTopDataDirLoc(aConfigD,dataName,localBucket)
    else:
      gsToDataDir[dataName] = makeTopDataDirGcp(aConfigD,dataName)

  # outfile defined differently if output is local or moved
  # to gcloud storage
  if usingLocalOut:
    outfName = args["out_file"]
  else:
    randNL = str(np.random.rand()).split('.')
    if len(randNL) < 2: randN = '0'
    else: randN = randNL[1]
    outfName = 'tempResult_'+randN+'.temp'
    # make sure the temp file & dir are in the local                                                 
    # machine's tmp directory                                                                        
    outfName = os.path.join('/tmp',outfName)
  if len(os.path.basename(outfName).split('.')) < 2:
    raise ValueError('output file must have an append')

  # create the temporary dir for file DL.  if the results
  # are being written to GCloud, this is also where the
  # local results file will be written (update outfName)
  tmpDir = '.'.join(outfName.split('.')[:-1]) + '_TEMP'
  if not(os.path.isdir(tmpDir)): os.mkdir(tmpDir)
  else: raise ValueError("temp dir already existed: "+tmpDir)
  if usingGcloudOut:
    # creating a sub-dir for the temp file so that the                                              
    # only files in the tmpDir will be from DL                                                      
    tmpSubDir = os.path.join(tmpDir,'Results')
    os.mkdir(tmpSubDir)
    outfName = os.path.join(tmpSubDir,outfName)
  outf = open(outfName,'w')

  headerL = ['date']
  for a in analysisL: headerL.extend(analysisD[a+"_columns"])
  outf.write('\t'.join(headerL)+'\n')
  mID = args["mouse_id"]

  f = open(args["devmap_file"])
  mousehouseText = f.read()
  f.close()
  devBlockL = getMappedBlocks(mousehouseText,mID)

  if args['one_block_test']:
    devBlockL = devBlockL[:1]

  getDataL = getDataGetter(gsToDataDir,usingLocBucket)
    
  # each of these blocks is a "week" from the DFI (one measure)
  for device,dateA,dateZ in devBlockL:
    
    anToResult = {'date':makeDateStr(dateA)}
    
    # each data source will be DL'ed once, and all
    # appropriate analyses run on it
    for dataSource in dataSourceL:

      dataL = getDataL(dateA,dateZ,dataSource,device,tmpDir)
      
      # analysis
      print(makeDateStr(dateA)+' analysis of '+dataSource+'...')
      for analysis in dataSrcToAnalyses[dataSource]:
      
        anToResult[analysis] = analysisD[analysis](dataL)

    c = [anToResult['date']]
    for a in analysisL: c.append(anToResult[a])    
    outf.write('\t'.join(list(map(str,c))) + '\n')

  outf.close()

  # if using GCloud, copy the results file to the cloud
  # then delete the local copy (gsutil mv does both)
  if usingGcloudOut:
    gsCommand = ("gsutil mv "+outfName+" "+gcOutfName).split()
    p = subprocess.Popen(gsCommand)
    (output,err) = p.communicate()
    os.rmdir(tmpSubDir)
    
  os.rmdir(tmpDir)
  print('Done.')

  
######## HELPER FUNCTIONS #########


def makeTopDataDirGcp(aConfigD,aType):
  tiDL = list(filter(lambda i:i['name']==aType, aConfigD['aInfoL']))
  if len(tiDL)==0: raise ValueError('analysis type missing: '+aType)
  if len(tiDL)!=1: raise ValueError('analysis type duplicated: '+aType)
  tiD = tiDL[0]
  return '/'.join(['gs:/',tiD['out_bucket'],tiD['out_folder']])

def makeTopDataDirLoc(aConfigD,aType,locMount):
  tiDL = list(filter(lambda i:i['name']==aType, aConfigD['aInfoL']))
  if len(tiDL)==0: raise ValueError('analysis type missing: '+aType)
  if len(tiDL)!=1: raise ValueError('analysis type duplicated: '+aType)
  tiD = tiDL[0]
  return os.path.join(locMount,tiD['out_folder'])

def makeDateStr(today):
  """for printing & internal representation"""
  yr,mo,day = today.year,today.month,today.day
  return '-'.join([str(yr),dtMdStr(mo),dtMdStr(day)])

def getFileAsDict(devMapFile):
  """evaluates the python code so that the
  values bound to variables can be accessed"""
  f = open(devMapFile)
  t = f.read()
  f.close()
  d = {}
  exec(t,d,d)
  return d

def dtMdStr(n):
  """helps reconcile single-digit numbers
  with two-digit day/month reps in paths"""
  if n >= 10: return str(n)
  else: return '0'+str(n)

def funcForDatetimeFromFile(date):
  """makes a function for combining date & time
  into a single datetime datum, using filename
  and given a pre-specified date"""
  def getDatetime(fname):
    fname = os.path.basename(fname)
    if len(fname)<5: raise ValueError('too short to contain time')
    fname = fname[:5]
    if fname[2]!='.': raise ValueError('missing dot for hh.mm time label')
    hr,mnt = int(fname[:2]),int(fname[3:5])
    yr,mo,day = date.year, date.month, date.day
    return DT.datetime(year=yr,month=mo,day=day,hour=hr,minute=mnt)
  return getDatetime

def makeDatePath(date):
  """makes a path with the combination of YYYY/MM/DD
  directories required by the video storage convention"""
  y,m,d = date.year,date.month,date.day
  yS,mS,dS = str(y),dtMdStr(m),dtMdStr(d)
  return '/'.join([yS,mS,dS])

def getDataGetter(gsToDataDir,usingLocBucket):
  # two alternative data collectors
  def collectorGcp(gsDataDir,device,datePath,tmpDir):
    gsDir = gsDataDir + device + '/' + datePath + '/'
    gsCommand = ("gsutil -m cp "+gsDir+"* "+tmpDir).split()
    p = subprocess.Popen(gsCommand)
    (output,err) = p.communicate()
  def collectorGcp_newNotReady(gsDataDir,device,datePath,tmpDir):
    gsDir = gsDataDir + device + '/' + datePath + '/'
    gsCommand = ("gsutil -m cp "+gsDir+"* "+tmpDir).split()
    p = subprocess.Popen(gsCommand)
    (output,err) = p.communicate()
    raise ValueError('in the middle of correcting')
    input_mov_project = analysisConfig['input_mov_project']
    input_mov_bucket = analysisConfig['input_mov_bucket']
    storage_client_in = storage.Client(project=in_mov_project)
    bucket_in = storage_client_in.bucket(in_mov_bucket)
    blob_in = bucket_in.blob(in_mov_blob)
    blob_in.download_to_filename(input_mov_local)
  def collectorLoc(gsDataDir,device,datePath,tmpDir):
    gsDir = gsDataDir + device + '/' + datePath + '/'
    for f in os.listdir(gsDir):
      oldF,newF = os.path.join(gsDir,f),os.path.join(tmpDir,f)
      shutil.copy(oldF,newF)
      os.chmod(newF, os.stat(newF).st_mode | stat.S_IRUSR)
  # assign the variable name to appropriate one
  if usingLocBucket: collectorUsed = collectorLoc
  else: collectorUsed = collectorGcp
  
  # now the function to be used
  def getDataL(dateA,dateZ,dataSource,device,tmpDir):
    gsDataDir = gsToDataDir[dataSource]
    """collects all of the data from the specified date block
    (starting at dateA, stopping at - NOT INCLUDING - dateZ)"""
    # all of the values will be stored here, with
    # keys that can be sorted chronologically
    dataD = {}
    dayStep = DT.timedelta(days=1)
    if gsDataDir[-1]!='/': gsDataDir += '/'

    # iterate through all of the days in the block
    dt = dateA
    while dt < dateZ:        
      # variables to hold current value while iterating
      today = dt
      tomorrow = dt + dayStep
      dt = tomorrow
      datePath = makeDatePath(today)
      getDatetime = funcForDatetimeFromFile(today)    
    
      # collect the data
      print(datePath+' download...')
      # collect the day's data from the cloud
      collectorUsed(gsDataDir,device,datePath,tmpDir)

      # read in the data, erase the files
      print(datePath+' reading...')
      fullFnameL = os.listdir(tmpDir)
      fullFnameL = list(map(lambda i: os.path.join(tmpDir,i), fullFnameL))
      fullFnameL = list(filter(lambda i: os.path.isfile(i), fullFnameL))
      # help for sorting files by time
      for fn in fullFnameL: dataD[getDatetime(fn)] = np.load(fn)
      for fname in fullFnameL: os.remove(fname)
          
    # now that it is NR, I will be able to sort
    # across the entire multi-day time interval
    dtFrDataL = [(dt,CONST_FRAME_PER_SEC,dataD[dt]) for dt in dataD.keys()]
    # sort based on file basenames (will sort by time)
    dtFrDataL.sort()
    return dtFrDataL

  # the function above will get the data
  return getDataL


### PARSING THE DEVICE MAPPING/DATA BLOCK FILE ###

def parseDatetimeStr(dts):
    dvt = dts.split('T')
    dateNL = list(map(int,dvt[0].split('-')))
    timeNL = list(map(int,dvt[1].split('.')[0].split(':')))
    yr,mo,dy = dateNL
    hr,mi,sc = timeNL
    return DT.datetime(year=yr,month=mo,day=dy,
                       hour=hr,minute=mi,second=sc)


def getMappedBlocks(mousehouseText,mouseID):
  # use the above resources to fill in the tables
  # I will require at least two full day's worth of data
  _MIN_DATA_DAYS = DT.timedelta(days=2)
  devDateL = []
  entries = list(filter(lambda i:i!='', mousehouseText.split('\n')))
  for i in entries:
    cL = i.split('\t')
    # the cage ID serves as the device ID here,
    # and the mouse IDs need to conversion
    devid,stdts,nddts,cname = cL[1:5]
    if cname==mouseID:
      stdt = parseDatetimeStr(stdts)
      nddt = parseDatetimeStr(nddts)
      devDateL.append( (devid,stdt,nddt) )
  return devDateL

    

def someFilters():
  # setting up the date windows; first day, collection                                                
  # begins partway through (this day will be omitted)                                                 
  _allObsTransL = [DT.datetime(year=2021,month=5,day=10)]
  _obsWindowLenL = [7,7,4,10,7,7,7,4,10,7,7,7,7,7,7,7,4,11]
  for _owl in _obsWindowLenL:
    _prior = _allObsTransL[-1]
    _allObsTransL.append(_prior + DT.timedelta(days=_owl))
  # Below, I'll use these sets of intervals to filter                                                 
  # for the set that overlaps with data for each mouse.                                               
  # I'll omit the first & last days from each interval                                                
  # since they will only contain partial data.  I will                                                
  # also apply a maximum length of 6 days                                                             
  _MAX_INTERVAL = 6
  _fullIntervalL = []
  for _iN in range(1,len(_allObsTransL)):
    _stDt = _allObsTransL[_iN-1] + DT.timedelta(days=1)
    _maxEndDt = _stDt + DT.timedelta(days=_MAX_INTERVAL)
    _endDt = min([_allObsTransL[_iN], _maxEndDt])
    # null device ID                                                                                
    _fullIntervalL.append( (_stDt,_endDt) )


if __name__ == "__main__": main()

