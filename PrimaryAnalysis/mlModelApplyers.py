import cv2
import numpy as np
import tensorflow as tf
import keras_segmentation
import keras_segmentation.models


class TfObjectIdentifier:
  def __init__(self,existingModelFile,categoryFile,boxExp=1.0):
    self._modFile = existingModelFile
    self._catFile = categoryFile
    self._boxExp = boxExp
    # this graph
    self._detection_graph = tf.Graph()
    with self._detection_graph.as_default():
      od_graph_def = tf.compat.v1.GraphDef()
      with tf.compat.v2.io.gfile.GFile(self._modFile, 'rb') as fid:
        serialized_graph = fid.read()
        print(self._modFile)
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')
    f = open(self._catFile)
    catText = f.read()
    f.close()
    self._category_index = {}
    for entry in catText.split('item {')[1:]:
      idNum = int(entry.split('id:')[1].split('\n')[0].strip())
      idName = entry.split('name:')[1].split('\n')[0].strip()[1:-1]
      self._category_index[idNum] = {'id':idNum, 'name':idName}
    self._sess = tf.compat.v1.Session(graph=self._detection_graph)
    # for my own convenience
    self._numToName = {}
    for d in self._category_index.values():
      self._numToName[d['id']] = d['name']
  def getBoxExpandVal(self): return self._boxExp
  def getClassIds(self):
    outD = {}
    for d in self._category_index.values():
      outD[d['name']] = d['id']
    return outD
  def getBoxes(self,image):
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image, axis=0)
    image_tensor = self._detection_graph.get_tensor_by_name('image_tensor:0')
    # Each box represents a part of the image where a particular object was detected.
    boxes = self._detection_graph.get_tensor_by_name('detection_boxes:0')
    # Each score represent how level of confidence for each of the objects.
    # Score is shown on the result image, together with the class label.
    scores = self._detection_graph.get_tensor_by_name('detection_scores:0')
    classes = self._detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = self._detection_graph.get_tensor_by_name('num_detections:0')
    # Actual detection.
    (boxes, scores, classes, num_detections) = self._sess.run(
          [boxes, scores, classes, num_detections],
          feed_dict={image_tensor: image_np_expanded})
    h,w,ch = image.shape
    bL,scL,numB = boxes[0],scores[0],num_detections[0]
    classL = classes[0]
    boxL = []
    for n in range(int(numB)):
       yA,yB = int(bL[n][0]*h),int(bL[n][2]*h)
       xA,xB = int(bL[n][1]*w),int(bL[n][3]*w)
       clName = self._numToName[classL[n]]
       boxL.append( Box(xA,yA,xB,yB,scL[n],clName) )
    return boxL

class Box:
  def __init__(self,x0,y0,x1,y1,score,label):
    self._x0, self._y0 = x0, y0
    self._x1, self._y1 = x1, y1
    self._score,self._label = score,label
  # recover coords with min/max values
  def xCenter(self): return (self._x0 + self._x1) / 2.0
  def yCenter(self): return (self._y0 + self._y1) / 2.0
  def xMin(self): return min([self._x0,self._x1])
  def yMin(self): return min([self._y0,self._y1])
  def xMax(self): return max([self._x0,self._x1])
  def yMax(self): return max([self._y0,self._y1])
  def score(self): return self._score
  def adjustSize(self,ratio,img):
    xMid = (self._x0+self._x1)/2.0
    yMid = (self._y0+self._y1)/2.0
    xHalf = ratio * (self.xMax() - self.xMin())/2.0
    yHalf = ratio * (self.yMax() - self.yMin())/2.0
    self._x0,self._x1 = int(xMid - xHalf),int(xMid + xHalf)
    self._y0,self._y1 = int(yMid - yHalf),int(yMid + yHalf)
    if self._x0 < 0: self._x0 = 0
    if self._y0 < 0: self._y0 = 0
    if self._x1 > img.shape[1]: self._x1 = img.shape[1]
    if self._y1 > img.shape[0]: self._y1 = img.shape[0]
  def copy(self):
    x0, y0 = self._x0, self._y0
    x1, y1 = self._x1, self._y1
    score,label = self._score,self._label
    return Box(x0,y0,x1,y1,score,label)


# separate out the mask-drawing
class KrSegModelApplyer:
    def __init__(self,segMod,nClass,inW,inH,modFile):
        self._segMod,self._nC = segMod,nClass
        self._inW,self._inH = inW,inH
        self._modFile = modFile
        modType = keras_segmentation.models.model_from_name[segMod]
        self._model = modType(n_classes=nClass,input_height=inH,input_width=inW)
        self._model.load_weights(modFile)
    def getMask(self,image):
        h,w = image.shape[:2]
        seg = self._model.predict_segmentation(image)
        # now I need to re-size the masks to match the image
        hS,wS = seg.shape
        segI = np.zeros( (hS,wS,3) )
        segI[:,:,0] = seg
        gt = keras_segmentation.data_utils.data_loader.get_segmentation_arr(segI,self._nC,w,h)
        gt = gt.argmax(-1)
        return gt.reshape((h,w))

class TfClassifier:
  def __init__(self,existingModelFile,categoryFile):
    self._modFile = existingModelFile
    self._catFile = categoryFile
    proto_as_ascii_lines = tf.compat.v1.io.gfile.GFile(categoryFile).readlines()
    self._labels = list(map(lambda i: i.rstrip(), proto_as_ascii_lines))
    # ## Load a (frozen) Tensorflow model into memory.
    self._detection_graph = tf.Graph()
    with self._detection_graph.as_default():
      od_graph_def = tf.compat.v1.GraphDef()
      with tf.compat.v1.io.gfile.GFile(self._modFile, 'rb') as fid:
        serialized_graph = fid.read()
        print(self._modFile)
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')
    self._sess = tf.compat.v1.Session(graph=self._detection_graph)
  def getClasses(self,image,spCl=None):
    # get the image tensor so I can re-size the image appropriately
    image_tensor = self._detection_graph.get_tensor_by_name('Placeholder:0')
    h,w = image.shape[:2]
    if h*w == 0:
      image = np.zeros(image_tensor.shape[1:])
    image_resized = cv2.resize(image,dsize=tuple(image_tensor.shape[1:3]))
    image_np_expanded = np.expand_dims(image_resized, axis=0)
    image_np_expanded = image_np_expanded.astype(np.float32)
    image_np_expanded /= 255
    answer_tensor = self._detection_graph.get_tensor_by_name('final_result:0')
    # Actual detection.
    (answer_tensor) = self._sess.run([answer_tensor],
                                     feed_dict={image_tensor: image_np_expanded})
    results = np.squeeze(answer_tensor)
    results = [(results[n],self._labels[n]) for n in range(len(self._labels))]
    return TfClassResult(results)
  def labels(self): return self._labels

class TfClassResult:
  # takes a list of score,label tuples
  def __init__(self,results):
    self._rD = {}
    for s,lb in results: self._rD[lb] = s
    self._lbmx = max(results)[1]
  def best(self): return self._lbmx
  def score(self,lb): return self._rD[lb]
  def labels(self): return self._rD.keys()

