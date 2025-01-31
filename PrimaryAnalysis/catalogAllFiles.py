# for creating a stored global accounting of all Vium files
# in a directory (original use: aio-age-001
import os, datetime, sys, argparse
import subprocess

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-a","--config_file",
                  help="the config file that specifies sources & which analyses to be run")
  ap.add_argument("-s","--path_source",
                  help="the data source ('input' for vids, 'wheel','box','minute' for outputs")
  ap.add_argument("-o","--out_file",
                  help="the result file (.txt)")
  ap.add_argument("-x","--file_app",
                  help="the file append (default=.mp4 for input, .npy for output)",
                  default="X")
  ap.add_argument("-b","--bucket_mount",
                  help="if the bucket is locally mounted, the folder/path for it",
                  default="")
  ap.add_argument("--bucket_out",
                  help="write out the gs bucket path, even with -b/--bucket_mount invoked",
                  action='store_true')
  args = vars(ap.parse_args())

  pathSrc = args["path_source"]
  
  fileAppend = args["file_app"]
  # select appropriate default, if necessary
  if fileAppend=="X":
    if pathSrc=='input': fileAppend = '.mp4'
    else: fileAppend = '.npy'

  # if it is a mounted bucket...
  bucketMounted = False
  if args["bucket_mount"]:
    bucketMounted = True
    bucketPath = args["bucket_mount"]
    if not(os.path.isdir(bucketPath)):
      raise ValueError("bucket mount path doesn't exist")
  # only relevant if bucket is mounted
  outAsBucket = args["bucket_out"]

  # I need the config file plus the analysis file
  # selection (or 'input'), and default/optional appends
  aConfig = configImporter(args['config_file'])

  if pathSrc=='input':
    srcProject = aConfig['input_mov_project']
    srcBucket = aConfig['input_mov_bucket']
    srcFolder = aConfig['input_mov_folder']
  else:
    acL = aConfig['aInfoL']
    acL = list(filter(lambda i: i['name']==pathSrc, acL))
    if len(acL)==0: raise ValueError('path_source not found')
    elif len(acL)>1: raise ValueError('path_source found multiple times')
    srcProject = acL[0]['out_project']
    srcBucket = acL[0]['out_bucket']
    srcFolder = acL[0]['out_folder']

  if bucketMounted:
    topDir = DirectorySourceDir(bucketPath)
    if outAsBucket:
      altTopDir = DirectoryBucket(srcProject,srcBucket)
      topDir.addOutputBucket(altTopDir)
  else:
    topDir = DirectoryBucket(srcProject,srcBucket)
  if srcFolder!='': topDir = DirectoryMid(srcFolder,topDir)
  
  outf = open(args['out_file'],'w')
  nFiles = recursiveFileWrite(topDir,fileAppend,outf)
  outf.close()
  
  print("Num files:\t"+str(nFiles))

  
def configImporter(pythonScript):
  d = {}
  f = open(pythonScript)
  exec(f.read(),d,d)
  f.close()
  return d


# depth-first search, imposing file append
# requirement
# RETURNS: number of files written
def recursiveFileWrite(currDir,append,fout):
  fCount = 0
  lenApp = len(append)
  for fObj in currDir.getFiles():
    name = fObj.name()
    if len(name) >= lenApp and name[-lenApp:]==append:
      fout.write(fObj.outputPath() + '\n')
      fout.flush()
      fCount += 1
  for dObj in currDir.getSubDirs():
    fCount += recursiveFileWrite(dObj,append,fout)
  return fCount

  
class DirectoryBucket:
  def __init__(self,project,bucket):
    self._project = project
    self._bucket = bucket
    self._hasMembers = False
  def name(self): return self._bucket
  def fullPath(self):
    return 'gs://'+self._bucket
  def outputPath(self):
    # no difference between the two
    return self.fullPath()
  def isBucket(self): return True
  def hasParent(self): return False
  def parent(self): return None
  def getSubDirs(self):
    getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._subdirs))
  def getFiles(self):
    self.getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._files))
  def getMembers(self):
    if not(self._hasMembers):
      self._hasMembers = True
      dirL,fileL = getDirMembers(self)
      self._files,self._subdirs = fileL,dirL

# alternative, if the files can be accessed locally
class DirectorySourceDir:
  def __init__(self,sourceDir):
    if len(sourceDir)==0 or sourceDir[0]!='/':
      raise ValueError('this is not a top-level source dir: '+sourceDir)
    self._sourceDir = sourceDir
    self._hasMembers = False
    self._useAlt = False
  def addOutputBucket(self,bucket):
    self._useAlt = True
    self._altSrc = bucket
  def name(self): return self._bucket
  def fullPath(self):
    return self._sourceDir
  def outputPath(self):
    if self._useAlt:
      return self._altSrc.fullPath()
    else:
      return self.fullPath()
  def isBucket(self): return False
  def hasParent(self): return False
  def parent(self): return None
  def getSubDirs(self):
    getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._subdirs))
  def getFiles(self):
    self.getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._files))
  def getMembers(self):
    if not(self._hasMembers):
      self._hasMembers = True
      dirL,fileL = getDirMembers(self)
      self._files,self._subdirs = fileL,dirL

class DirectoryMid:
  # instance methods
  def __init__(self,name,parent):
    self._parent = parent
    self._isBucket = parent.isBucket()
    self._name = name
    self._hasMembers = False
    self._files = []
    self._subdirs = [] # Directory objects
  def name(self): return self._name
  def fullPath(self):
    if self._parent==None: return self._name
    else: return os.path.join(self._parent.fullPath(),self._name)
  def outputPath(self):
    if self._parent==None: return self._name
    else: return os.path.join(self._parent.outputPath(),self._name)    
  def isBucket(self): return self._isBucket
  def hasParent(self): return True
  def parent(self): return self._parent
  def getSubDirs(self):
    self.getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._subdirs))
  def getFiles(self):
    self.getMembers()
    return list(map(lambda i:DirectoryMid(i,self), self._files))
  def getMembers(self):
    if not(self._hasMembers):
      self._hasMembers = True
      dirL,fileL = getDirMembers(self)
      self._files,self._subdirs = fileL,dirL


def getDirMembers(dirObj):  
  print(dirObj.fullPath())
  if dirObj.isBucket():
    proc = subprocess.Popen(["gsutil","ls",dirObj.fullPath()],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out,err = proc.communicate()
    out = out.decode('ascii')
    entryL = list(filter(lambda i: i.find("gs://")==0, out.split('\n')))
    dirL = list(filter(lambda i: i[-1]=='/', entryL))
    dirL = list(map(lambda i: i[:-1].split('/')[-1], dirL))
    fileL = list(filter(lambda i: i[-1]!='/', entryL))
    fileL = list(map(lambda i: i.split('/')[-1], fileL))
  else:
    allItems = os.listdir(dirObj.fullPath())
    fpF = lambda i: os.path.join(dirObj.fullPath(),i)
    fileL = list(filter(lambda i: os.path.isfile(fpF(i)), allItems))
    dirL = list(filter(lambda i: os.path.isdir(fpF(i)), allItems))
  return dirL,fileL


if __name__ == "__main__": main()

