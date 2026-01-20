# Execute with the command below at the terminal
# "C:\path\to\Slicer\program\Slicer.exe" --python-script C:\path\to\your\code\centerline_extraction_slicer.py
# (refer https://www.slicer.org/wiki/Documentation/Nightly/Developers/Python_scripting)

#  Written by Do Kim <donny8@naver.com> 

import os
import pickle
import numpy as np
import nibabel as nib
from nibabel.affines import apply_affine
import utils
import sys
sys.path.append("D:/vmtk/VMTK-based-Centerline-Extraction-main")  # .py のあるフォルダ
import ExtractCenterline_slicer
import vtk.util.numpy_support

SAVE_INFO = True

# Specific to my dataset 
case_id = '00000000'
segmentName = 'Segment_1'
serverPath = r"\path\to\your\data"


img = nib.load("E:/coronary_data_600/1.label.nii.gz")
affine = img.affine


targetClass="left"
endpointName = f"Endpoints_{case_id}_{targetClass}"
endpointmodelName = f"Endptmodel_{case_id}_{targetClass}"
centermodelName = f"Model_{case_id}_{targetClass}"
voronoimodelName = f"Voronoi_{case_id}_{targetClass}"
centertableName = f"Properties_{case_id}_{targetClass}"
centercurveName = f"Curve_{case_id}_{targetClass}"

endpointModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", endpointmodelName)
centerlineModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", centermodelName)
voronoiModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", voronoimodelName)
centerlinePropertiesTableNode =  slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode" ,centertableName)
centerlineCurveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", centercurveName)

# Step1: Load Segmentation: From Path to 'vtkMRMLSegmentationNode' type           
seg_path = "E:/coronary_data_600/1.label.nii.gz" # Specific to my dataset 
if not(os.path.exists(seg_path)):
    continue
segmentationNode = slicer.util.loadSegmentation(seg_path)
segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
extractLogic = ExtractCenterline_slicer.ExtractCenterlineLogic()

# Step2: SegmentationNode to vtkPolyData
inputSurfacePolyData = extractLogic.polyDataFromNode(segmentationNode, segmentID)
print('DEBUG', inputSurfacePolyData)
writer = vtk.vtkSTLWriter()
writer.SetInputData(inputSurfacePolyData)
writer.SetFileName("D:/vmtk/VMTK-based-Centerline-Extraction-main/inputSurfacePolyData.stl")
writer.Write()   