import os, datetime as DT
import numpy as np
import scipy.stats as SPS
import sys, os, datetime as DT, argparse

DFI_PARAMS = ['gait.w','gait.f',
              'circ.w','circ.f',
              'spins','nest',
              'coat.q','bw.delta',
              'coat.br']

class Entry:
    def __init__(self,headL,valueL):
        expHeadL = ['date','spins/day','hertz',
                    'circ.wh','coat_q(sobel)',
                    'bwt_dlt(g/day)','bed_mov(pxls)',
                    'circ.fl','kpix/sec','color(8-bit)']
        self._inD = {}
        if len(headL)!=len(valueL):
            raise ValueError('header & values must be same length')
        for n in range(len(headL)):
            self._inD[headL[n]] = valueL[n]
        for h in expHeadL:
            if not(h in self._inD):
                raise ValueError('missing header: '+h)
    def getDateStr(self): return self._inD['date']
    def getDfiValue(self,param):
        # I'll define 'fv' in each case and limit it to (0,1)
        # at the end
        if param=='gait.w':
          if self._inD['hertz']=='N/A': iv = float('nan')
          else: iv = float(self._inD['hertz'])
        elif param=='gait.f':
          if self._inD['kpix/sec']=='N/A': iv = float('nan')
          else: iv = float(self._inD['kpix/sec'])
        elif param=='circ.w':
          if self._inD['circ.wh']=='N/A': iv = float('nan')
          else: iv = float(self._inD['circ.wh'])
        elif param=='circ.f':
          if self._inD['circ.fl']=='N/A': iv = float('nan')
          else: iv = float(self._inD['circ.fl'])
        elif param=='spins':
          if self._inD['spins/day']=='N/A': iv = float('nan')
          else: iv = float(self._inD['spins/day'])
        elif param=='nest':
          if self._inD['bed_mov(pxls)']=='N/A': iv = float('nan')
          else: iv = float(self._inD['bed_mov(pxls)'])
        elif param=='coat.q':
          if self._inD['coat_q(sobel)']=='N/A': iv = float('nan')
          else:
            iv = float(self._inD['coat_q(sobel)'])
            if self._inD['color(8-bit)']=='N/A': cc = 0
            else: cc = float(self._inD['color(8-bit)'])
            if cc <= 30: iv += 2.0
            elif cc >= 70: iv += 4.0
        elif param=='bw.delta':
          if self._inD['bwt_dlt(g/day)']=='N/A': iv = float('nan')
          else: iv = abs(float(self._inD['bwt_dlt(g/day)']))
        elif param=='coat.br':
          if self._inD['color(8-bit)']=='N/A': iv = float('nan')
          else: iv = float(self._inD['color(8-bit)'])          
        else: raise ValueError('bad param')
        # truncate within acceptable range
        if np.isnan(iv): iv = 'N/A'
        return iv

    
def parseFile(fname):
    entryL = []
    f = open(fname)
    header = f.readline().rstrip().split('\t')
    line = f.readline()
    while line:
        cols = line.rstrip().split('\t')
        entryL.append( Entry(header,cols) )
        line = f.readline()
    f.close()
    return entryL


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-i","--dfi_dir",
                  help="directory of input files")
  ap.add_argument("-o","--output_file",
                  help="the ouput file of DFI scores (.tsv)")
  args = vars(ap.parse_args())

  in_dir = args["dfi_dir"]
  outfile = args["output_file"]

  infileL = os.listdir(in_dir)
  infileL = list(filter(lambda i: len(i)>4 and i[-4:]=='.tsv', infileL))

  outf = open(outfile,'w')
  headL = ['mouse','date']
  headL.extend(DFI_PARAMS)
  outf.write('\t'.join(headL) + '\n')
  
  for infname in infileL:
      mouseId = infname[:-4]
      entryL = parseFile(os.path.join(in_dir,infname))
      for e in entryL:
        cols = [mouseId,e.getDateStr()]
        dfScoreL = list(map(e.getDfiValue,DFI_PARAMS))
        cols.extend(dfScoreL)
        outf.write('\t'.join(map(str,cols)) + '\n')
  outf.close()

if __name__ == "__main__": main()


