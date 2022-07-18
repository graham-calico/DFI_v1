import sys, os, argparse


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-a","--config_file",
                  help="the config file that specifies sources & which analyses to be run")
  ap.add_argument("-s","--path_source",
                  help="the data source ('input' for vids, 'wheel','box','minute' for outputs")
  ap.add_argument("-m","--movie_file",
                  help="the movie file-of-files (source files)")
  ap.add_argument("-r","--result_file",
                  help="the analysis result file-of-files")
  ap.add_argument("-o","--out_file",
                  help="the output file-of-line-numbers")
  args = vars(ap.parse_args())
  
  movieFile = args["movie_file"]
  resultFile = args["result_file"]
  outFile = args["out_file"]
  if os.path.isfile(outFile):
    raise ValueError('outfile already exists, would have been over-written')

  # I need the config file plus the analysis file
  # selection
  pathSrc = args["path_source"]
  aConfig = configImporter(args['config_file'])
  acL = aConfig['aInfoL']
  acL = list(filter(lambda i: i['name']==pathSrc, acL))
  if len(acL)==0: raise ValueError('path_source not found')
  elif len(acL)>1: raise ValueError('path_source found multiple times')
  # the answers:
  movieDir = aConfig['input_mov_folder']
  resultDir = acL[0]['out_folder']

  # functions for collecting fingerprints
  getMovName = makeFileFingerprinter(movieDir)
  getResName = makeFileFingerprinter(resultDir)

  # collect results + check NR
  f = open(resultFile)
  resLineD = {}
  line,resN = f.readline(),0
  while line:
    resLineD[getResName(line.strip())] = None
    resN += 1
    line = f.readline()
  f.close()
  print("Num result files:\t"+str(resN))
  if resN != len(resLineD):
    print("NR result files:\t"+str(len(resLineD)))

  # see which movies are still waiting on results
  f = open(movieFile)
  missL = []
  line,movN = f.readline(),0
  while line:
    movN += 1 # 1-indexed line numbers
    if not(getMovName(line.strip()) in resLineD):
      missL.append(movN)
    line = f.readline()
  f.close()
  print("Num movie files:\t"+str(movN))
  print("Num movie files w/out results:\t"+str(len(missL)))

  # write the outfile of the missing movie file line numbers
  f = open(outFile,'w')
  for i in missL: f.write(str(i)+'\n')
  f.close()

  
# assumes that the file name begins with a unique
# 24h-clock time stamp, formatted "HH.MM"
def makeFileFingerprinter(hostDir):
  intCharRefD = {}
  for n in '0123456789': intCharRefD[n] = None
  def getFingerprint(fullPath):
    locPath = fullPath.split(hostDir)[-1]
    dirPath,fName = os.path.split(locPath)
    # run some checks on fName
    if len(fName) < 5:
      raise ValueError('file name too short: '+fullPath)
    if fName[2]!='.':
      raise ValueError('file name bad format HH.MM (.): '+fullPath)
    for n in [0,1]:
      if not(fName[n] in intCharRefD):
        raise ValueError('file name bad format HH.MM (H): '+fullPath)
    for n in [3,4]:
      if not(fName[n] in intCharRefD):
        raise ValueError('file name bad format HH.MM (M): '+fullPath)
    return os.path.join(dirPath,fName[:5])
  return getFingerprint

def configImporter(pythonScript):
  d = {}
  f = open(pythonScript)
  exec(f.read(),d,d)
  f.close()
  return d

  
if __name__ == "__main__": main()
