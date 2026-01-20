# -*- coding: utf-8 -*-
"""
Created on Wed Jan 14 15:53:15 2026

@author: hattori

This file contains code derived from the ExtractCenterline module
of the 3D Slicer VMTK extension.

Original authors:
Andras Lasso, Daniel Haehn, Luca Antiga, Steve Pieper

Modifications:
- Logic-only extraction
- Integration into PcatMeasure extension

"""


import os
import sys

import re
import pickle
import numpy as np
import logging
logging.basicConfig(level=logging.INFO)

import qt
import ctk
import vtk
from vtk.util import numpy_support
from vtk.numpy_interface import dataset_adapter as dsa
import vtk.util.numpy_support

import slicer
from slicer.ScriptedLoadableModule import *

#module_dir = os.path.dirname(os.path.abspath(__file__))
#utils_dir = os.path.join(module_dir, "utils")
#if utils_dir not in sys.path:
#    sys.path.insert(0, utils_dir)

from utils.branch import showMultiCheckPopup
from utils.cal_startpoint import cal_start_point
from utils.save_overlay import exportSegToLabel
from utils.save_overlay import saveOverlayImage
from utils.save_poly import save_poly
from utils.create_curved_cylinder_mask import create_curved_cylinder_mask
from utils.getCTvaluesFromSegmentation import getCTvaluesFromSegmentation
from utils.extract_centerline_logic import ExtractCenterlineLogic
logging.getLogger().setLevel(logging.DEBUG)

#
# module information
#
class PcatMeasure(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Pcat measure extension"
        parent.categories = ["Cardiology"]
        parent.contributors = ["hattori (Yamagata university)",
                               "kinoshita (Yamagata university)",
                               "Based on VMTK ExtractCenterline (Lasso et al.)"]
        parent.helpText = """
        Pericoronary adipose tissue (PCAT) measurement module.
        This module computes coronary centerlines and quantifies PCAT attenuation.
        """
        parent.acknowledgementText = """Developed for PCAT project.
        This module uses and modifies code from the Extract Centerline module
        of the 3D Slicer Vascular Modeling Toolkit (VMTK) extension.
        
        Original authors:
        Andras Lasso (PerkLab),
        Daniel Haehn (Boston Children's Hospital),
        Luca Antiga (Orobix),
        Steve Pieper (Isomics).
        
        The original code is distributed under the 3D Slicer license."""

#
# widget_GUI
#
class PcatMeasureWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        if not hasattr(self, "logic"):
            self.logic = PcatMeasureLogic()
        #self.logic = PcatMeasureLogic()

        self.extractLogic = ExtractCenterlineLogic()
        self.resetWidgetState()
        self.layout = qt.QVBoxLayout()
        
        
        
        
        
        
        # title
        titleLabel = qt.QLabel("Pcat measure")
        titleLabel.setStyleSheet("font-weight: bold; font-size: 14px; color: #2a82da;")
        self.layout.addWidget(titleLabel)

        # file path information
        self.ctPathLabel = qt.QLabel("CT: No file selected.")
        self.segPathLabel = qt.QLabel("Segmentation: No file selected.")
        self.pathLabel = qt.QLabel("No file selected.")
        self.layout.addWidget(self.pathLabel)
        self.layout.addWidget(self.ctPathLabel)
        self.layout.addWidget(self.segPathLabel)

        # button
        self.loadCTButton2 = qt.QPushButton("[1] : Get CT Node")
        self.addPointButton = qt.QPushButton("[2] : Starting Point")
        self.loadSegButton2 = qt.QPushButton("Load Seg (file dialog)")
        self.loadSegButton3 = qt.QPushButton("[2]:Select branches")
        self.loadSegButton4 = qt.QPushButton("[3]:Analysis PCAT")
        self.clearButton = qt.QPushButton("Clear All")
        self.clearButton2 = qt.QPushButton("Clear (except CT)")
        #self.clearButton3 = qt.QPushButton("Clear (except CT and Seg)")
        self.resetViewButton = qt.QPushButton("Reset slice views")
        self.backButton = qt.QPushButton("Back to Coronary Centerline Cross Section")
        self.showInflammationButton = qt.QPushButton("[4] : Show PCAT inflammation")

        #checkbox
        self.saveOverlayCheckBox = qt.QCheckBox("Save Overlay Images")
        self.saveOverlayCheckBox.checked = False
        self.loadCheckBox = qt.QCheckBox("Scene(True) or dialog(False)")
        self.loadCheckBox.checked = True
                
        #CT Volume selector 
        ctLabel = qt.QLabel("Select CT Volume (from Scene)")
        ctLabel.setStyleSheet("font-weight: bold;")
        
        
        self.ctSelector = slicer.qMRMLNodeComboBox()
        self.ctSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.ctSelector.selectNodeUponCreation = False
        self.ctSelector.addEnabled = False
        self.ctSelector.removeEnabled = False
        self.ctSelector.noneEnabled = True
        self.ctSelector.setMRMLScene(slicer.mrmlScene)
        
                        
        #segmentation selector
        segLabel = qt.QLabel("Select Segmentation (from Scene)")
        segLabel.setStyleSheet("font-weight: bold;")
        
        # --- get segment name from Segmentation ---
        self.segmentSelector = slicer.qMRMLSegmentSelectorWidget()
        self.segmentSelector.setMRMLScene(slicer.mrmlScene)
        self.segmentSelector.setToolTip("Select segment to process")
              
        
        # --- Coronary artery selection ---
        arteryLabel = qt.QLabel("Target coronary artery")
        arteryLabel.setStyleSheet("font-weight: bold;")
        
        # artery selection
        self.rcaRadio = qt.QRadioButton("RCA")
        self.ladRadio = qt.QRadioButton("LAD")
        self.LcxRadio = qt.QRadioButton("LCX")
        # default
        self.rcaRadio.setChecked(True)
        
        # ButtonGroup（）
        self.arteryButtonGroup = qt.QButtonGroup()
        self.arteryButtonGroup.addButton(self.rcaRadio)
        self.arteryButtonGroup.addButton(self.ladRadio)
        self.arteryButtonGroup.addButton(self.LcxRadio)
        
        
        
        # pcat range start mm slider
        self.startSlider = slicer.qMRMLSliderWidget()
        self.startSlider.minimum = 0
        self.startSlider.maximum = 100
        self.startSlider.singleStep = 1
        self.startSlider.decimals = 1
        self.startSlider.valueChanged.connect(self.onStartSliderChanged)
        
        #  pcat range end mm slider
        self.endSlider = slicer.qMRMLSliderWidget()
        self.endSlider.minimum = 0
        self.endSlider.maximum = 150
        self.endSlider.singleStep = 1
        self.endSlider.decimals = 1
        self.endSlider.valueChanged.connect(self.onEndSliderChanged)
                
        # range sliderのdefault値を設定
        self.setDefaultPCATRange()
        
        # rayout
        formLayout = qt.QFormLayout()
        formLayout.setLabelAlignment(qt.Qt.AlignLeft)
        formLayout.setFormAlignment(qt.Qt.AlignLeft | qt.Qt.AlignTop)
        formLayout.setHorizontalSpacing(8)
        formLayout.setVerticalSpacing(6)
        
        label = qt.QLabel("Load data from:")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.loadCheckBox)
        
        # --- Target coronary artery (GroupBox) ---
        arteryWidget = qt.QWidget()
        arteryLayout = qt.QHBoxLayout(arteryWidget)
        arteryLayout.setContentsMargins(0, 0, 0, 0)
        arteryLayout.setSpacing(12)
        arteryLayout.addWidget(self.rcaRadio)
        arteryLayout.addWidget(self.ladRadio)
        arteryLayout.addWidget(self.LcxRadio)
        arteryLayout.addStretch(1)  
        
        label = qt.QLabel("Target coronary artery")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, arteryWidget)
        
        label = qt.QLabel("Select CT Volume")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.ctSelector)
        
        label = qt.QLabel("Select Segmentation")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.segmentSelector)
        
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.loadCTButton2)

        #label = qt.QLabel("")
        #label.setStyleSheet("font-weight: bold;")
        #formLayout.addRow(label, self.addPointButton)
           
        pcatTitle = qt.QLabel("PCAT range")
        pcatTitle.setStyleSheet("font-weight: bold;")
        formLayout.addRow(pcatTitle, qt.QWidget())  
        
        formLayout.addRow("Start (mm)", self.startSlider)
        formLayout.addRow("End (mm)", self.endSlider)
        
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.loadSegButton3)
        
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.loadSegButton4)
        formLayout.addItem(qt.QSpacerItem(0, 16, qt.QSizePolicy.Minimum, qt.QSizePolicy.Fixed))
        
        label = qt.QLabel("Option")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.showInflammationButton)
     
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.resetViewButton)
        
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        
        label = qt.QLabel("")
        label.setStyleSheet("font-weight: bold;")
        
        formLayout.addRow(label, self.clearButton)
        formLayout.addRow(label, self.clearButton2)
        formLayout.addRow(label, self.backButton)

        self.layout.addLayout(formLayout)

        
        
        # connect signal
        self.loadCTButton2.connect("clicked(bool)", self.onLoadCT)
        self.loadSegButton3.connect("clicked(bool)", self.onSelect_branches)
        self.loadSegButton4.connect("clicked(bool)", self.onAnalysys_pcat)
        self.resetViewButton.connect("clicked()",self.onResetViewButtonClicked)
        self.addPointButton.connect("clicked(bool)", self.onEnableMarkups)
        self.clearButton.clicked.connect(self.onClearAllNodes)
        self.clearButton2.clicked.connect(self.onClearSegNodes)
        #self.clearButton3.clicked.connect(self.onClearcenterlineNodes)
        self.rcaRadio.toggled.connect(self.onArteryChanged)
        self.ladRadio.toggled.connect(self.onArteryChanged)
        self.LcxRadio.toggled.connect(self.onArteryChanged)
        self.showInflammationButton.connect('clicked(bool)', self.onShowInflammation)
        self.backButton.connect("clicked()",self.onBackButtonClicked)
        
        self.layout.addStretch(1)
        self.parent.layout().addLayout(self.layout)
#%% Reset every time you change modules      
    def resetWidgetState(self):    
        
        self.ctNode = None
        self.segmentationNode=None
        self.segNode = None
        self.seg2Node = None
        self.PCAT_seg_filtered = None
        self.fat_segmentId=None
        self.coronary_artery_name = "RCA"
        self.caseNodeIDs = []
        self.caseNodeIDs_2 = []
        self.keepIDs=[]
        self.coordinates = []
        self.ct_file_path = None
        self.ct_file_name = None
        self.selected_ids=None
        self.total_selected_length=None
        self.save_dir_output=None
        self.save_dir=None
        self.mergedCenterlines=None
        self.cell_pt =None
        self.coord_mm = {}
        self.coord_voxel = {}
        self.default_branch_id= []
        self.selected_ids = []
        self.textActors = []
        
        #self.observerTag = None
        
    def setCaseNodeIDs(self, nodeIDs,nodeIDs_2):
        self.caseNodeIDs = list(nodeIDs)
        self.caseNodeIDs_2 = list(nodeIDs_2)   
   

    def clearCaseNodes(self,caseNodeIDs, keepNodeIDs=None):
        import slicer
    
        keepNodeIDs = set(keepNodeIDs or [])
    
        for nodeID in list(caseNodeIDs):
            if nodeID in keepNodeIDs:
                continue
    
            node = slicer.mrmlScene.GetNodeByID(nodeID)
            if node:
                slicer.mrmlScene.RemoveNode(node)
    
        # 残ったものだけ再登録
        caseNodeIDs = [
            nid for nid in caseNodeIDs
            if slicer.mrmlScene.GetNodeByID(nid)
        ]   
            
#%%%    ボタン押した時の動作    
    #[1] : Get CT Node button sceneからかdialogからかで処理変えている    
    def onLoadCT(self):
        import slicer
        if self.loadCheckBox.checked:
            self.ctNode = self.ctSelector.currentNode()
            if self.ctNode is None:
                slicer.util.errorDisplay("No CT Volume selected.")
                return
        
            self.ctPathLabel.setText(f"CT (Scene): {self.ctNode.GetName()}")
        
            slicer.util.setSliceViewerLayers(background=self.ctNode)
            #slicer.app.layoutManager().resetSliceViews()
            #slicer.app.layoutManager().resetThreeDViews()
            
            storageNode = self.ctNode.GetStorageNode()
            if storageNode and storageNode.GetFileName():
                self.ct_file_path = storageNode.GetFileName()
                self.ct_file_name = os.path.basename(self.ct_file_path)
            else:
                
                self.ct_file_path = None
                self.ct_file_name = self.ctNode.GetName()
            logging.info("--Loaded CT")
        else:
            filePath = qt.QFileDialog.getOpenFileName(
            None,
            "Select CT image file",
            "",
            "Image files (*.nii *.nii.gz *.nrrd *.mha *.mhd *.dcm);;All files (*)"
            )
    
            if not filePath:
                slicer.util.infoDisplay("No CT file selected.")
                return
    
            self.ctPathLabel.setText(f"CT: {filePath}")
    
            try:
                self.ctNode = slicer.util.loadVolume(filePath)
                if self.ctNode:
                    slicer.util.setSliceViewerLayers(background=self.ctNode)
                    slicer.app.layoutManager().resetSliceViews()
                    slicer.app.layoutManager().resetThreeDViews()
                else:
                    slicer.util.errorDisplay("Failed to load CT image.")
                
                self.ct_file_path = filePath
                self.ct_file_name = os.path.basename(filePath)
            except Exception as e:
                slicer.util.errorDisplay(f"Error loading CT file:\n{str(e)}")    
                
            self.caseNodeIDs.append(self.ctNode.GetID())
            self.keepIDs.append(self.ctNode.GetID())

            logging.info("--Loaded CT")
            #self.keepIDs = [self.ctNode.GetID()]
            
    
#%%    # radio buttonの設定        
    def onArteryChanged(self):
        if self.rcaRadio.isChecked():
            self.coronary_artery_name = "RCA"
        elif self.ladRadio.isChecked():
            self.coronary_artery_name = "LAD"
        elif self.LcxRadio.isChecked():
            self.coronary_artery_name = "LCX"
        
        self.setDefaultPCATRange()
        
    def setDefaultPCATRange(self):
        if self.coronary_artery_name == "RCA":
            self.start_mm = 10
            self.end_mm = 50
    
        elif self.coronary_artery_name in ["LCA", "LCX"]:
            self.start_mm = 0
            self.end_mm = 40
    
        else:
            self.start_mm = 0
            self.end_mm = 40
    
        # スライダーへ反映
        self.startSlider.value = self.start_mm
        self.endSlider.value = self.end_mm
        
    def onStartSliderChanged(self, value):
        self.start_mm = value
    
        # start <= end を保証
        if self.start_mm > self.end_mm:
            self.end_mm = self.start_mm
            self.endSlider.value = self.end_mm
    def onEndSliderChanged(self, value):
        self.end_mm = value
    
        if self.end_mm < self.start_mm:
            self.start_mm = self.end_mm
            self.startSlider.value = self.start_mm
#%%    #view reset button
    def onResetViewButtonClicked(self):
        lm = slicer.app.layoutManager()
    
        lm.sliceWidget("Red").sliceLogic().GetSliceNode().SetOrientationToAxial()
        lm.sliceWidget("Green").sliceLogic().GetSliceNode().SetOrientationToCoronal()
        lm.sliceWidget("Yellow").sliceLogic().GetSliceNode().SetOrientationToSagittal()
#%%    #goto cccs module   
    def onBackButtonClicked(self):
        
        ###slicer.util.reloadScriptedModule("CoronaryCenterlineCrossSection")  this is forced
        ccWidget = slicer.modules.coronarycenterlinecrosssection.widgetRepresentation().self()
        ccWidget.logic.reset()
        ccWidget.resetWidgetState()
        slicer.util.selectModule("CoronaryCenterlineCrossSection")

#%% 起始部の点を配置する
    def onEnableMarkups(self):
        # 既存の Markups ノードを取得または作成
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("PickedPoints")
        if not markupsNode:
            markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "PickedPoints")
    
        # Interaction Node を取得
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    
        # このノードを現在のPlaceターゲットに設定
        interactionNode.SetCurrentInteractionMode(interactionNode.Place)

        # Markupsを配置対象に指定
        slicer.modules.markups.logic().SetActiveListID(markupsNode)
#%% データ削除
    def onClearAllNodes(self):
        import slicer
        slicer.mrmlScene.Clear(0)
        logging.info("All displayable nodes cleared.")
        
    def onClearSegNodes(self):
        self.clearCaseNodes(caseNodeIDs=self.caseNodeIDs_2,keepNodeIDs=self.keepIDs)
        logging.info("All nodes except the CT have been cleared.")    
    
    
        
#%% inflammatinoをjpeg化する  
    def onShowInflammation(self):
        volumeNode = self.ctNode
        segmentationNode = self.PCAT_seg_filtered
        fatID =self.fat_segmentId
        
        if segmentationNode is None:
            slicer.util.errorDisplay("No segmentationNode.")
            return
        
        if segmentationNode is None:
            slicer.util.errorDisplay("No segmentation available.")
            return
    
        pcatSegID = fatID
        if pcatSegID is None:
            slicer.util.errorDisplay("PCAT_fat segment not found. Run Step 2 first.")
            return
    
        #
        # Original CT を PCAT 部分だけ色付けした RGB 画像に変換
        #
        coloredNode = self.logic.createColorizedOriginal(
            volumeNode,
            segmentationNode,
            pcatSegID
        )
    
        #
        # SliceView に表示（Foreground に色付き CT）
        #
        lm = slicer.app.layoutManager()
        for viewName in lm.sliceViewNames():
            sv = lm.sliceWidget(viewName).sliceLogic()
            sv.GetSliceCompositeNode().SetBackgroundVolumeID(volumeNode.GetID())
            sv.GetSliceCompositeNode().SetForegroundVolumeID(coloredNode.GetID())
            sv.GetSliceCompositeNode().SetForegroundOpacity(1.0)  # 完全に色付き CT を表示
    
        slicer.util.infoDisplay("PCAT-colored CT image created and displayed.")
     
    
#%%
    def BranchSelectionAccepted(self, selected_ids, total_selected_length):
        self.selected_ids = selected_ids
        self.total_selected_length = total_selected_length

        logging.info("--Selected branch IDs: %s", self.selected_ids)
        logging.info("--Total length: %s", self.total_selected_length)
    
    
    
    

        

#%% selectbranchボタンを押したら 
    def onSelect_branches(self):
        logging.info("step0:Analysis target = %s", self.coronary_artery_name)
        import slicer
        if self.loadCheckBox.checked==False:
            
        
            filePath = qt.QFileDialog.getOpenFileName(
                None,
                "Select segmentation file",
                "",
                "Segmentation files (*.seg.nrrd *.nii *.nii.gz *.nrrd);;All files (*)"
            )
    
            if not filePath:
                slicer.util.infoDisplay("No segmentation file selected.")
                return
    
            self.segPathLabel.setText(f"Segmentation: {filePath}")
        
        
        referenceVolumeNode = self.ctNode  # CT
        
        ijkToRas = vtk.vtkMatrix4x4()
        referenceVolumeNode.GetIJKToRASMatrix(ijkToRas)
        
        affine = np.array([
            [ijkToRas.GetElement(r, c) for c in range(4)]
            for r in range(4)])
                
        
        
        
        endpointName = "Endpoints"
        endpointmodelName = "Endptmodel"
        centermodelName = "Model"
        voronoimodelName = "Voronoi"
        centertableName = "Properties"
        centercurveName = "　  cc"
        
        # 保存先フォルダ
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.save_dir_output=os.path.join(base_dir,"output")
        
        # フォルダがなければ作成
        os.makedirs(self.save_dir_output, exist_ok=True)
        safe_ct_name = self.logic.sanitize_filename(self.ct_file_name)
        safe_ct_name = safe_ct_name.replace(".", "_")

        
        self.save_dir = os.path.join(self.save_dir_output, safe_ct_name)
        os.makedirs(self.save_dir, exist_ok=True)
        
        # ファイルパス
        save_path = os.path.join(self.save_dir, "01_inputSurfacePolyData.vtk")
        # Slicer add node
        endpointModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", endpointmodelName)
        centerlineModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", centermodelName)
        voronoiModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", voronoimodelName)
        centerlinePropertiesTableNode =  slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode" ,centertableName)
        centerlineCurveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", centercurveName)
        self.caseNodeIDs.append(endpointModelNode.GetID())
        self.caseNodeIDs.append(centerlineModelNode.GetID())
        self.caseNodeIDs.append(voronoiModelNode.GetID())
        self.caseNodeIDs.append(centerlinePropertiesTableNode.GetID())
        self.caseNodeIDs.append(centerlineCurveNode.GetID())

        #球体を非表示
        #centerlineCurveNode.GetDisplayNode().SetVisibility(False)

        # Step1: Load Segmentation: From Path to 'vtkMRMLSegmentationNode' type        
        logging.info("step1:Load Segmentation")
      
        if self.loadCheckBox.checked:
            self.segmentationNode = self.segmentSelector.currentNode()
            if self.segmentationNode is None:
                slicer.util.errorDisplay("Segmentation no selected")
                return
            
            segmentID = self.segmentSelector.currentSegmentID()
            if not segmentID:
                slicer.util
        else:
            seg_path=filePath
            self.segmentationNode = slicer.util.loadSegmentation(seg_path)
            # ファイルロード時も SegmentSelector にセット
            self.segmentSelector.setSegmentationNode(self.segmentationNode)
            segmentID = self.segmentSelector.currentSegmentID()
            if not segmentID:
                # 自動フォールバック（1つ目）
                segmentation = self.segmentationNode.GetSegmentation()
                if segmentation.GetNumberOfSegments() == 0:
                    slicer.util.errorDisplay("No segments in segmentation")
                    return
                segmentID = segmentation.GetNthSegmentID(0)

        # Step2: SegmentationNode to vtkPolyData
        logging.info("step2:SegmentationNode to vtkPolyData")
        inputSurfacePolyData = self.extractLogic.polyDataFromNode(self.segmentationNode, segmentID)
        #logging.info('DEBUG', inputSurfacePolyData)
        SAVE_VTK=True
        save_poly(SAVE_VTK, inputSurfacePolyData, os.path.join(self.save_dir, f"01_inputSurfacePolyData_{self.coronary_artery_name}.vtk"))
                 
               
        
        targetNumberOfPoints = 5000.0
        decimationAggressiveness = 4 
        subdivideInputSurface = False
        
        if inputSurfacePolyData.GetNumberOfPoints() == 0:
            slicer.util.errorDisplay("Input surface is empty")
            return
        preprocessedPolyData = self.extractLogic.preprocess(inputSurfacePolyData, targetNumberOfPoints, decimationAggressiveness, subdivideInputSurface)
        save_poly(SAVE_VTK, preprocessedPolyData, os.path.join(self.save_dir, f"02_preprocessedPolyData_{self.coronary_artery_name}.vtk"))
        
        # Step3: Extract Centerline Network (Approximated Centerline)
        logging.info("step3:Extract Centerline Network")
        endPointsMarkupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", endpointName)
        #非表示
        endPointsMarkupsNode.GetDisplayNode().SetVisibility(False)
        networkPolyData = self.extractLogic.extractNetwork(preprocessedPolyData, endPointsMarkupsNode, computeGeometry=True)  # Voronoi 
        # Create Centerline Model
        endpointModelNode.SetAndObserveMesh(networkPolyData)
        self.caseNodeIDs.append(endpointModelNode.GetID())
        self.caseNodeIDs.append(endPointsMarkupsNode.GetID())

        # Step4: Get EndPoints ( AutoDetect )
        logging.info("step4:Get EndPoints")
        #startPointPosition=None
        
        startPointPosition_list = []
        
        """#手動でマークアップをする場合。
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("PickedPoints")

        n = markupsNode.GetNumberOfControlPoints()
        for i in range(n):
            ras = [0.0, 0.0, 0.0]
            markupsNode.GetNthControlPointPositionWorld(i, ras)  # 
            startPointPosition_list.append(ras)
        aortaCenter = [0, 0, 0]
        startPointPosition = self.logic.closest_point(startPointPosition_list, aortaCenter)
        """
        #startPointPosition = startPointPosition_list[0]
        #初期値
        
        #複数マークアップがある場合に一番近い点を取得
        
        
        paramNode = slicer.mrmlScene.GetFirstNodeByName("PCATParameters")
        if not paramNode:
            print("return1")
            return None
    
        s = paramNode.GetParameter("CenterlineStartPointRAS")
        if not s:
            print("return2")
            return None
        startPointPosition = np.array([float(v) for v in s.split(",")])
        
        self.coordinates.append(startPointPosition)
        #print(self.coordinates)
        #
        #print("startPoint",startPoint)
        #print("startPointPosition",startPointPosition)
        endpointPositions = self.extractLogic.getEndPoints(networkPolyData, startPointPosition) # AutoDetect the endpoints. type: List
        
        endPointsMarkupsNode.RemoveAllControlPoints()
        for position in endpointPositions:
            endPointsMarkupsNode.AddControlPoint(vtk.vtkVector3d(position))

        # Step5: Extract Centerline, Voronoi
        logging.info("step5:Get Extract Centerline, Voronoi")
        centerlinePolyData, voronoiDiagramPolyData = self.extractLogic.extractCenterline(preprocessedPolyData, endPointsMarkupsNode)
        centerlineModelNode.SetAndObserveMesh(centerlinePolyData)          
        voronoiModelNode.SetAndObserveMesh(voronoiDiagramPolyData)  

        # Step6: Extract centerlineCurves
        logging.info("step6:Extract centerlineCurves")
        self.mergedCenterlines, centerlineProperties, self.cell_pt = self.extractLogic.createCurveTreeFromCenterline(centerlinePolyData, centerlineCurveNode, centerlinePropertiesTableNode) 
            
        save_poly(SAVE_VTK, self.mergedCenterlines, os.path.join(self.save_dir,f"03_mergedCenterlines_{self.coronary_artery_name}.vtk"))
        
        
        
        
        #####################################################
        # Preliminary for the Radius Calculation in each curve
        #各セル（枝）ごとの点IDを取得
        #mergedCenterlines の各セル（曲線単位）に含まれる 点のインデックスリスト を保存
        #後で、曲線ごとの点列の抽出や幾何量の関連付けに使う
        #####################################################
        self.ce_ll_pt_LIST = {}
        for cell in range(self.mergedCenterlines.GetNumberOfCells()):
            self.ce_ll_pt_LIST[cell] = []
            getCell = self.mergedCenterlines.GetCell(cell)
            for idx in range(getCell.GetPointIds().GetNumberOfIds()):
                pt = getCell.GetPointIds().GetId(idx)
                self.ce_ll_pt_LIST[cell].append(pt)
    
        # Step7: Extract centerlineCurve info
        logging.info("step7:Extract and save centerlineCurve info")
        SAVE_INFO = True
        if(SAVE_INFO):
            r1 = self.mergedCenterlines.GetPointData().GetArray('Radius')
            
            self.radius_arr = vtk.util.numpy_support.vtk_to_numpy(r1)    
            
            
            with open(os.path.join(self.save_dir,f'00_centerCurve_radius_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.radius_arr, f, pickle.HIGHEST_PROTOCOL)

            properties_dict = {}
            for columnName in [self.extractLogic.lengthArrayName, self.extractLogic.curvatureArrayName, self.extractLogic.torsionArrayName, self.extractLogic.tortuosityArrayName]:
                vtk_arr = centerlineProperties.GetPointData().GetArray(columnName)
                properties_dict[columnName] = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            with open(os.path.join(self.save_dir,f'00_centerCurve_property_dict_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(properties_dict, f, pickle.HIGHEST_PROTOCOL)
                
            with open(os.path.join(self.save_dir,f'00_centerCurve_cell_idx_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.cell_pt, f, pickle.HIGHEST_PROTOCOL)

            vtk_arr = self.mergedCenterlines.GetPoints().GetData()
            array = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            
            for cell in self.cell_pt:
                cell_array = array[self.ce_ll_pt_LIST[cell]]
                self.coord_mm[cell] = cell_array
                #self.coord_voxel[cell] = apply_affine(np.linalg.inv(affine), array[self.cell_pt[cell]])
                ras_points = array[self.cell_pt[cell]]  # (N,3) RAS
                self.coord_voxel[cell] = self.logic.rasToIjkPoints(self.ctNode, ras_points)
            with open(os.path.join(self.save_dir,f'00_centerCurve_coord_mm_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.coord_mm, f, pickle.HIGHEST_PROTOCOL)
            with open(os.path.join(self.save_dir,f'00_centerCurve_coord_voxel_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.coord_voxel, f, pickle.HIGHEST_PROTOCOL)

        logging.info("step8:Auto get branch IDs")
        groupIdsArrayName = 'GroupIds'
        groupIdsArray = self.mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
    
        # 2. ユニークな GroupIds を取得
        uniqueGroupIds = list(set(groupIdsArray.GetTuple1(i) for i in range(groupIdsArray.GetNumberOfTuples())))
        #uniqueGroupIds.sort()  # 一応順番揃える
        numGroups = len(uniqueGroupIds)
        
        
        
        
        total_lengths = []
        for i in range(self.mergedCenterlines.GetNumberOfCells()):
            
            points_branch = self.coord_mm[i]  # shape = (N, 3)            
            diffs = np.diff(points_branch, axis=0)
            segment_lengths = np.linalg.norm(diffs, axis=1)
            total_length = np.sum(segment_lengths)
            #logging.info("i",i,"total_length",total_length)
            total_lengths.append(total_length)
        #self.coronary_artery_name="RCA"
        #logging.info("total_lengthが1なら分岐なし、１より多いなら分岐あるとして条件分岐するか？",total_lengths)
        #複数分岐がある場合やLCA→LAD,LCX分岐のセグメンテーションの場合ある程度自動判定してやる
        """
        if len(total_lengths)>1:
            #logging.info("分岐ある旧バージョン")
            ###############################################################
            #もしかしたらこのbifurcation_idsの分岐はいらないと思う．
            ###############################################################
            if self.coronary_artery_name in ("LAD", "LCX"):
                bifurcation_ids = self.logic.find_first_bifurcation(mergedCenterlines=self.mergedCenterlines,
                                                                    coord_mm=self.coord_mm,
                                                                    tol=1.0)
                if len(bifurcation_ids) < 2:
                    raise RuntimeError("LM bifurcation not found")
                
                lcx_root, lad_root = self.loigc.classify_LAD_LCX(branch_ids=bifurcation_ids,
                                                                 coord_mm=self.coord_mm)
                
            if self.coronary_artery_name == "RCA":
                cumulative_length = 0
                for i in range(len(total_lengths)):
                    cumulative_length += total_lengths[i]
                    self.default_branch_id.append(i)
                    if cumulative_length >= 50:
                        break
            elif self.coronary_artery_name=="LAD":
                
                self.default_branch_id = self.collect_until_length(lad_root,
                                                                   mergedCenterlines=self.mergedCenterlines,
                                                                   coord_mm=self.coord_mm,
                                                                   target_len=40.0,
                                                                   angle_th=np.deg2rad(30))
            elif self.coronary_artery_name=="LCX":
                self.default_branch_id = self.collect_until_length(lcx_root, 
                                                                   mergedCenterlines=self.mergedCenterlines,
                                                                   coord_mm=self.coord_mm,
                                                                   target_len=40.0,
                                                                   angle_th=np.deg2rad(30))
            #branch_id はとりあえず自動で選んだPCAT領域に対応するID
        else:
            #logging.info("1本バージョン")
            
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                self.default_branch_id.append(i)
        """       
        
        if self.coronary_artery_name == "RCA":
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                self.default_branch_id.append(i)
                if cumulative_length >= 50:
                    break
        elif self.coronary_artery_name=="LAD":
            
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                self.default_branch_id.append(i)
                if cumulative_length >= 50:
                    break
        elif self.coronary_artery_name=="LCX":
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                self.default_branch_id.append(i)
                if cumulative_length >= 50:
                    break
        
        
        logging.info("--get branch ID is %s",self.default_branch_id)
        
        
        
        #CT画像上で取得した起始部の座標を取得###################################################
        """#手動でマークアップをする場合。
        # Markupsノードを取得
        if not markupsNode:
            slicer.util.warningDisplay("No markups found. Please enable markups and place points first.")
            return
    
        n = markupsNode.GetNumberOfFiducials()
        if n == 0:
            slicer.util.warningDisplay("No points placed yet.")
            return
    
        self.coordinates = []
        for i in range(n):
            ras = [0.0, 0.0, 0.0]
            markupsNode.GetNthFiducialPosition(i, ras)
            self.coordinates.append(ras)
            logging.info("Start point %d: R=%.2f, A=%.2f, S=%.2f",i + 1, ras[0], ras[1], ras[2])
    
        """
        
       
    
    
    
        
        ##############元のコードから．長さとかIDを表示   VIL=>view_id_lengthの略
        group_ids = self.mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
        #logging.info("group_ids",group_ids)
        points = self.mergedCenterlines.GetPoints()
        vivid_colors = [(1, 0, 0),(0, 1, 0),(0, 0, 1),(1, 1, 0),(1, 0, 1),(0, 1, 1),(1, 0.5, 0),(0.5, 0, 1),
                         (1, 0, 0.5),(0.5, 0.5, 0),(0, 0.5, 1),(0, 1, 0.5),(0.5, 1, 0), (1, 0.25, 0),(0.25, 0, 1),
                        (0, 1, 0.25),(0.75, 0, 1),(1, 0, 0.75),(0.5, 1, 1),(1, 1, 0.5)]
        
        for i in range(self.mergedCenterlines.GetNumberOfCells()):
            cell_VIL = self.mergedCenterlines.GetCell(i)
            group_VIL = group_ids.GetValue(i)
            branch_id_VIL = uniqueGroupIds.index(group_VIL)
            
            # 差分をとってユークリッド距離を計算
            points_branch_VIL  = self.coord_mm[i]  # shape = (N, 3)            
            diffs_VIL = np.diff(points_branch_VIL, axis=0)  # 連続する点の差分ベクトル（N-1, 3）
            segment_lengths_VIL = np.linalg.norm(diffs_VIL, axis=1)  # 各セグメントの長さ
            total_length_VIL = np.sum(segment_lengths_VIL)  # 合計
         
            # ブランチの中点のインデックスを取得
            mid_index_VIL = cell_VIL.GetNumberOfPoints() // 2
            point_id_VIL = cell_VIL.GetPointId(mid_index_VIL)
            position_VIL = points.GetPoint(point_id_VIL)
            
            text_source = vtk.vtkVectorText()
            text_source.SetText(f"→{branch_id_VIL} [{total_length_VIL:.1f}mm]")
            
            # 厚みを付ける
            extrude = vtk.vtkLinearExtrusionFilter()
            extrude.SetInputConnection(text_source.GetOutputPort())
            extrude.SetExtrusionTypeToNormalExtrusion()
            extrude.SetVector(0,0,1)
            extrude.SetScaleFactor(0.5)
            extrude.Update()
            
            text_mapper = vtk.vtkPolyDataMapper()
            text_mapper.SetInputConnection(extrude.GetOutputPort())
            
            text_actor = vtk.vtkFollower()
            text_actor.SetMapper(text_mapper)
            text_actor.GetProperty().SetColor(vivid_colors[i])
            text_actor.GetProperty().SetAmbient(0.5)
            text_actor.GetProperty().SetDiffuse(0.5)
            text_actor.SetScale(2, 2, 2)
            text_actor.SetPosition(position_VIL)
            
            renderer = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer()
            renderer.AddActor(text_actor)
            
            camera = renderer.GetActiveCamera()
            text_actor.SetCamera(camera)
            
            # アンチエイリアス強化
            slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().SetMultiSamples(8)
            renderer.ResetCameraClippingRange()
            slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().Render()
            
            
            
            self.textActors.append(text_actor)            
                        
            
            
            
            
            
        
        logging.info("step9:check branch")
    
        
        self.total_selected_length = 0.0
            
        
        displayNode = self.segmentationNode.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility3D(False)
        
        
        
        showMultiCheckPopup(
            total_lengths,
            default_ids=self.default_branch_id,
            coronary_name=self.coronary_artery_name,
            onAcceptedCallback=self.BranchSelectionAccepted
        )
        
        
#%% analysys pcatを押したら        
        
    def onAnalysys_pcat(self):
        
        #selecetedIDSで選んだbrannchのcenterlineの座標を連結
        points_culmulative_mm =  np.concatenate([self.coord_mm[i] for i in self.selected_ids], axis=0)#coord_mm[self.branch_id]  # shape = (N, 3)
        points_culmulative_voxel =  np.concatenate([self.coord_voxel[i] for i in self.selected_ids], axis=0)#coord_voxel[self.branch_id]  # shape = (N, 3)
        
        ###############################
        #coordinates変数はRASorLAS座標．
        #points_culmulative_voxelはIJK座標なので変換が必要
        ###############################
        #マークアップスの座標をRASに変換
        ras_point = self.coordinates[0]  # [-14.61, 204.66, 105.45]
        
        # RAS→IJK行列を取得
        rasToIJK = vtk.vtkMatrix4x4()
        self.ctNode.GetRASToIJKMatrix(rasToIJK)
        
        # 同次座標で計算
        ijk_h = [0, 0, 0, 1]
        rasToIJK.MultiplyPoint([ras_point[0], ras_point[1], ras_point[2], 1], ijk_h)
        
        # 最初の3つが IJK
        ijk = ijk_h[:3]
        
        # 必要なら整数にする
        ijk_int = [round(v) for v in ijk]
        
        #RAS 形式
        #start_corrdinate=cal_start_point(coordinates[0],points_culmulative_voxel) 
        
        #IJK　形式
        start_corrdinate=cal_start_point(ijk_int,points_culmulative_voxel)
        
        points_culmulative=points_culmulative_mm[start_corrdinate:,:]
       
        # 各点の差分ベクトル（連続する点の移動）
        diffs_culmulative = np.diff(points_culmulative, axis=0)  # (N-1, 3)

        # 各区間の長さ（ユークリッド距離）
        segment_lengths_culmulative = np.linalg.norm(diffs_culmulative, axis=1)  # (N-1,)

        # 累積距離の配列：先頭に0を付けて [0, d1, d1+d2, ...]
        cumulative_distances = np.insert(np.cumsum(segment_lengths_culmulative), 0, 0.0)  # shape = (N,)
        
        if self.coronary_artery_name=="RCA":
            mask_PCAT = (cumulative_distances >= self.start_mm) & (cumulative_distances <= self.end_mm)
            
        else:
            mask_PCAT = (cumulative_distances >= self.start_mm) & (cumulative_distances <= self.end_mm)
            
        # まず各branchのpoint idリストを順番に取り出して
        lists = [self.ce_ll_pt_LIST[bid] for bid in self.selected_ids]
        #logging.info("self.selected_ids",self.selected_ids)
        # それらをまとめて1次元のnumpy配列にする
        point_ids = np.array([pid for sublist in lists for pid in sublist])  # 　←だと分岐のところの点が重複している。多分重複はよくなさそう       
        
        
        points_vtk_array = self.mergedCenterlines.GetPoints().GetData()
        self.points_np = vtk.util.numpy_support.vtk_to_numpy(points_vtk_array)
        
        point_ids_after_start_selected_=point_ids[start_corrdinate:]
        
        ###########################################
        # 区間を絞る（10〜20mm）
        ###########################################
        selected_ids2 = point_ids_after_start_selected_[mask_PCAT]

        cumulative_distance_mask=cumulative_distances[mask_PCAT]
        if selected_ids2.shape[0] < 2:
            raise ValueError("need two point data")
            
        ############################################
        # 新しい vtkPoints と polyLine を作る
        ############################################
        new_points = vtk.vtkPoints()
        new_lines = vtk.vtkCellArray()
                             
        ############################################
        #                   
        # 点を登録
        ############################################
        id_map = {}  # 元のpoint_id → 新しい順番
        for i, pid in enumerate(selected_ids2):
            #logging.info(i,pid)
            coord = self.points_np[pid]
            new_points.InsertNextPoint(coord)
            id_map[pid] = i    
            
        # polyline作成（直線的な連続接続）
        ###########################################
        line = vtk.vtkPolyLine()
        line.GetPointIds().SetNumberOfIds(len(selected_ids2))
        for i in range(len(selected_ids2)):
            line.GetPointIds().SetId(i, i)
        new_lines.InsertNextCell(line)
        ############################################
        # vtkPolyData に登録
        ############################################
        new_polydata = vtk.vtkPolyData()
        new_polydata.SetPoints(new_points)
        new_polydata.SetLines(new_lines)
        ############################################
        # vtkとPCATを測定する範囲をvtkとして保存
        ############################################
        writer = vtk.vtkPolyDataWriter()
        if self.coronary_artery_name=="RCA":

            writer.SetFileName(os.path.join(self.save_dir,f"04_branch{self.selected_ids}_{self.coronary_artery_name}_10to50mm.vtk"))
        else:
            writer.SetFileName(os.path.join(self.save_dir,f"04_branch{self.selected_ids}_{self.coronary_artery_name}_0to40mm.vtk"))
        writer.SetInputData(new_polydata)
        writer.Write()
        
        ##################################################################################################################################
        #　ここからextract pcat2
        ##################################################################################################################################
        #radius_arr=>radius_data
        #cell_pt=>cell_id_data
        logging.info("step10:create artery & PCAT")
        radius_data=self.radius_arr
        cell_id_data=self.cell_pt
        lists = [cell_id_data[bid] for bid in self.selected_ids]
        branch_id_list = np.array([pid for sublist in lists for pid in sublist])  
        branch_0_coords_all = self.points_np[branch_id_list]
        branch_0_radius_all = radius_data[branch_id_list]
        branch_0_coords=branch_0_coords_all[start_corrdinate:,:]
        branch_0_radius=branch_0_radius_all[start_corrdinate:]
        
        branch_0_coords_PCAT=branch_0_coords[mask_PCAT]
        branch_0_radius_PCAT=branch_0_radius[mask_PCAT]  
        
        
        # === RAS → IJK 変換 ===
        
        ##################元のコードはこれ
        #coord_mm = np.hstack([branch_0_coords_PCAT, np.ones((len(branch_0_coords_PCAT), 1))])
        #coord_voxel = (inv_affine @ coord_mm.T).T[:, :3]
        #coord_voxel = np.round(coord_voxel).astype(int)
        #coord_voxel=np.abs(coord_voxel)
        ##################
        ras_to_ijk = vtk.vtkMatrix4x4()
        self.ctNode.GetRASToIJKMatrix(ras_to_ijk)
        
        def ras_to_ijk_np(points_ras):
            ijk_list = []
            for p in points_ras:
                dst = [0,0,0,0]
                vtk.vtkMatrix4x4.MultiplyPoint(ras_to_ijk, [p[0], p[1], p[2], 1], dst)
                ijk_list.append(dst[:3])
            return np.round(np.array(ijk_list)).astype(int)
        
        coord_voxel = ras_to_ijk_np(branch_0_coords_PCAT)
                
                            
        #半径に応じた血管とPCAT領域を作成．なお，tubepolyデータはModelデータになっている
        import inspect
        tube_polydata = create_curved_cylinder_mask(branch_0_coords_PCAT, branch_0_radius_PCAT*3.0)
        logging.info("--Tube Points(not zero): %s", tube_polydata.GetNumberOfPoints())  # ← 0でないこと
        if tube_polydata.GetNumberOfPoints() == 0:
            raise ValueError("Tube Points zero")
             
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(os.path.join(self.save_dir,f"05_{self.coronary_artery_name}_PCAT_Coronary_Wall.vtk"))
        writer.SetInputData(tube_polydata)
        writer.Write()
                        
        logging.info("step11:extract PCAT area")
        
        # tube_polydata は RAS 座標の PolyData
        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        modelNode.SetAndObservePolyData(tube_polydata)
        modelNode.SetName("seg_artery_PCAT")
        
        segNode_artery_PCAT = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Artery_seg")
        # セグメンテーションの座標系を CT と合わせる（RAS）
        segNode_artery_PCAT.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        # モデルをセグメントとして追加
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(
            modelNode, segNode_artery_PCAT
            )         
        # ---------------------------------------------------
        # 1) 新しい SegmentationNode に2つを結合
        # ---------------------------------------------------
        seg_artery=self.segmentationNode
        mergedSeg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "MergedSeg")
        mergedSeg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        logic = slicer.modules.segmentations.logic()
        
        # 2) A -> LabelMap にエクスポート
        labelA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        # ExportAllSegmentsToLabelmapNode か ExportVisibleSegmentsToLabelmapNode のどちらか環境で使える方を
        # 
        try:
            logic.ExportAllSegmentsToLabelmapNode(seg_artery, labelA, self.ctNode)
        except Exception:
            logic.ExportVisibleSegmentsToLabelmapNode(seg_artery, labelA, self.ctNode)
        #logging.info("Exported seg_artery ->", labelA.GetName(), labelA.GetID())
        
        # 3) B -> LabelMap にエクスポート
        labelB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        try:
            logic.ExportAllSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)
        except Exception:
            logic.ExportVisibleSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)

        logic.ImportLabelmapToSegmentationNode(labelA, mergedSeg)
        seg = mergedSeg.GetSegmentation()
        segmentIdA = seg.GetNthSegmentID(seg.GetNumberOfSegments() - 1)

        # 5) labelB を mergedSeg に import
        logic.ImportLabelmapToSegmentationNode(labelB, mergedSeg)
        segmentIdB = seg.GetNthSegmentID(seg.GetNumberOfSegments() - 1)

        # 6) 確認：mergedSeg の segment list を表示
        ids = seg.GetSegmentIDs()

        workSeg_sub = self.logic.cloneSegmentation(mergedSeg, "work_PCAT_subtract",self.ctNode)
        
        self.logic.subtractSegment(workSeg_sub,self.ctNode,segmentIdB,segmentIdA)
        
        PCAT_seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "PCAT_seg")
        PCAT_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "tempLabel_sub")
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(workSeg_sub,[segmentIdB],labelNode,self.ctNode)
        
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelNode,PCAT_seg)
        
        # cleanup
        #slicer.mrmlScene.RemoveNode(labelNode)
        #slicer.mrmlScene.RemoveNode(workSeg_sub)
        self.caseNodeIDs_2.append(PCAT_seg.GetID())

        self.caseNodeIDs.append(segNode_artery_PCAT.GetID())
        self.caseNodeIDs.append(labelNode.GetID())
        self.caseNodeIDs.append(workSeg_sub.GetID())
        self.caseNodeIDs.append(modelNode.GetID())
        #self.caseNodeIDs.append(PCAT_seg.GetID())
        #self.keepIds.append(PCAT_seg.GetID())


        
        
        workSeg_int = self.logic.cloneSegmentation(mergedSeg, "work_PCAT_intersect",self.ctNode)
        self.caseNodeIDs.append(workSeg_int.GetID())

        
        
        
        self.logic.intersectSegment(workSeg_int,self.ctNode,segmentIdB,segmentIdA)
        
        PCAT_artery_seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "PCAT_artery_seg")
        PCAT_artery_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "tempLabel_int")
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(workSeg_int,[segmentIdB],labelNode,self.ctNode)
        
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelNode,PCAT_artery_seg)
        
        # cleanup
        #slicer.mrmlScene.RemoveNode(labelNode)
        #slicer.mrmlScene.RemoveNode(workSeg_int)
        self.caseNodeIDs.append(PCAT_artery_seg.GetID())

        self.caseNodeIDs.append(labelNode.GetID())
        self.caseNodeIDs.append(workSeg_int.GetID())

                
        
        # ---- 5) 不要な labelNode を削除 ----
        #slicer.mrmlScene.RemoveNode(labelA)
        #slicer.mrmlScene.RemoveNode(labelB)
        #slicer.mrmlScene.RemoveNode(labelNode)
        #slicer.mrmlScene.RemoveNode(mergedSeg)
        self.caseNodeIDs.append(labelA.GetID())
        self.caseNodeIDs.append(labelB.GetID())
        self.caseNodeIDs.append(labelNode.GetID())
        self.caseNodeIDs.append(mergedSeg.GetID())

        
        
        displayNode = segNode_artery_PCAT.GetDisplayNode()
              
        if displayNode:
            displayNode.SetVisibility(False)   
        
        
        ######################################################
        # 作成したPCAT_segは円柱なので，閾値処理した場合の形状にする
        ######################################################
        self.PCAT_seg_filtered  = self.logic.cloneSegmentation(PCAT_seg, "PCAT_filterd",self.ctNode)        
        
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentEditorNode"
        )
        segmentEditorNode.SetAndObserveSegmentationNode(self.PCAT_seg_filtered )
        segmentEditorNode.SetAndObserveMasterVolumeNode(self.ctNode)
        
        segmentation = self.PCAT_seg_filtered .GetSegmentation()
        self.fat_segmentId = segmentation.GetNthSegmentID(0)
        
        # enum を数値指定
        segmentEditorNode.SetMaskMode(1)   # InsideSingleSegment
        segmentEditorNode.SetMaskSegmentID(self.fat_segmentId)
        
        segmentEditorNode.SetOverwriteMode(2)  # OverwriteAllSegments
        
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        
        segmentEditorNode.SetSelectedSegmentID(self.fat_segmentId)
        
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()
        
        effect.setParameter("MinimumThreshold", "-190")
        effect.setParameter("MaximumThreshold", "-30")
        
        effect.self().onApply()
        
        # cleanup
        segmentEditorWidget = None
        #slicer.mrmlScene.RemoveNode(segmentEditorNode)
        self.caseNodeIDs.append(segmentEditorNode.GetID())
        self.caseNodeIDs_2.append(self.PCAT_seg_filtered.GetID())
        #self.keepIDs.append(PCAT_seg_filtered.GetID())
        
        
        
        segmentationdisp = PCAT_seg.GetSegmentation()
        segmentIDdisp = segmentationdisp.GetNthSegmentID(0)  # or segmentation.GetSegmentIdBySegmentName("PCAT")
        segmentdisp = segmentationdisp.GetSegment(segmentIDdisp)
        segmentdisp.SetColor(1.0, 1.0, 0.0)   
        segmentationdisp = self.PCAT_seg_filtered.GetSegmentation()
        segmentIDdisp = segmentationdisp.GetNthSegmentID(0)  # or segmentation.GetSegmentIdBySegmentName("PCAT")
        segmentdisp = segmentationdisp.GetSegment(segmentIDdisp)
        segmentdisp.SetColor(0.0, 1.0, 1.0)   
        
        # 赤 (1.0, 0.0, 0.0)

        # 緑segmentdisp.SetColor(0.0, 1.0, 0.0)
        
        # 青segmentdisp.SetColor(0.0, 0.0, 1.0)
        
        # 黄色segmentdisp.SetColor(1.0, 1.0, 0.0)
        
        # シアンsegmentdisp.SetColor(0.0, 1.0, 1.0)
        
        # マゼンタsegmentdisp.SetColor(1.0, 0.0, 1.0)
        
        # 白segmentdisp.SetColor(1.0, 1.0, 1.0)
        
        
        segmentationdisp2 = PCAT_artery_seg.GetSegmentation()
        segmentIDdisp2 = segmentationdisp2.GetNthSegmentID(0)
        # or segmentation.GetSegmentIdBySegmentName("PCAT")
        segmentdisp2 = segmentationdisp2.GetSegment(segmentIDdisp2)
        segmentdisp2.SetColor(0.0, 0.0, 1.0)
        
        logging.info("step12:cal PCAT value")
        ct_values,PCAT_value_list,PCAT_value = getCTvaluesFromSegmentation(PCAT_seg, self.ctNode,self.ct_file_path,self.coronary_artery_name,self.save_dir_output,ijk_int)
        
        logging.info("--PCAT HU: %s", PCAT_value)
         
        pcatLabelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            "PCAT_labelmap"
        )
        # export
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
            PCAT_seg,
            pcatLabelNode
        )
       
        #  中身チェック
        imageData = pcatLabelNode.GetImageData()
        if imageData is None or imageData.GetPointData().GetScalars() is None:
            raise RuntimeError("PCAT labelmap is empty")
       
       
        # ---- save ----
        ok = slicer.util.saveNode(pcatLabelNode, os.path.join(self.save_dir,f"07_pcat_{self.coronary_artery_name}.nii.gz"))
        
        
        pcatarteryLabelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            "PCAT_artery_labelmap"
        )
        # export
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
            PCAT_artery_seg,
            pcatarteryLabelNode
        )
       
        #  中身チェック
        imageData2 = pcatarteryLabelNode.GetImageData()
        if imageData2 is None or imageData2.GetPointData().GetScalars() is None:
            raise RuntimeError("PCAT artry labelmap is empty")
       
       
        # ---- save ----
        ok = slicer.util.saveNode(pcatarteryLabelNode, os.path.join(self.save_dir,f"06_artery_analysis_range_{self.coronary_artery_name}.nii.gz"))
        
        
        self.caseNodeIDs.append(pcatLabelNode.GetID())
        self.caseNodeIDs.append(pcatarteryLabelNode.GetID())
        self.clearCaseNodes(caseNodeIDs=self.caseNodeIDs)
       
        
        
        if self.saveOverlayCheckBox.checked:
            overlay_dir = os.path.join(self.save_dir, "overlay")
            os.makedirs(overlay_dir, exist_ok=True)
            
            logging.info("now save overlay")
            labelNode = exportSegToLabel(PCAT_seg, self.ctNode)
            
            saveOverlayImage(
                self.ctNode,
                labelNode,
                outputDir=overlay_dir
            )
        

    
class PcatMeasureLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        pass
        
    def hu_to_color(self, hu):
        """
        HU を -190〜-30 の範囲で 0〜1 に正規化し、
        その値で #00f5d4（低）〜 #fee440（高）を線形補間する。
        """

        # 1) HU を 0〜1 に正規化
        hu_min = -190.0
        hu_max = -30.0
        t = (hu - hu_min) / (hu_max - hu_min)
        t = np.clip(t, 0.0, 1.0)

        # 2) 色の定義（RGB 0〜255）
        c_low = np.array([0x4c, 0xd9, 0x64], dtype=float) # #4cd964（グリーン）
        c_high = np.array([0xf3, 0x42, 0x13], dtype=float) # #f34213（オレンジレッド）

        # 3) 線形補間
        rgb = (1 - t) * c_low + t * c_high
        return rgb.astype(np.uint8)
    
        
    def createColorizedOriginal(self, volumeNode, segmentationNode, pcatSegID):
        
        # --- 1) Original CT を取得 ---
        ct = slicer.util.arrayFromVolume(volumeNode)

        # ---  Window / Level を適用（Window=800, Level=250） ---
        window = 800.0
        level = 250.0

        minHU = level - window / 2.0  # -150
        maxHU = level + window / 2.0  # 650

        ct_wl = (ct - minHU) / (maxHU - minHU)
        ct_norm = np.clip(ct_wl * 255.0, 0, 255).astype(np.uint8)

        # --- 2) PCAT mask を取得 ---
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        #  Export 後に中身があるかチェック
        
        ids = vtk.vtkStringArray()
        ids.InsertNextValue(pcatSegID)

        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
            segmentationNode, ids, labelmapNode, volumeNode
        )
        if labelmapNode.GetImageData() is None:
                    raise RuntimeError("Labelmap export failed: no image data created") 
        mask = slicer.util.arrayFromVolume(labelmapNode).astype(bool)

        # --- 3) HU 値を取得 ---
        hu = slicer.util.arrayFromVolume(volumeNode)

        # --- 4) RGBA 画像を作成 ---
        h, w, d = ct.shape
        rgba = np.zeros((h, w, d, 4), dtype=np.uint8)

        # Window/Level 適用済み CT を RGB に変換
        rgba[..., 0] = ct_norm
        rgba[..., 1] = ct_norm
        rgba[..., 2] = ct_norm
        rgba[..., 3] = 255

        # --- 5) PCAT 部分だけ hu_to_color() で色付け ---
        hu_vals = hu[mask]
        colors = np.array([self.hu_to_color(v) for v in hu_vals])

        rgba[mask, 0] = colors[:, 0]  # R
        rgba[mask, 1] = colors[:, 1]  # G
        rgba[mask, 2] = colors[:, 2]  # B

        # --- 6) VectorVolume として保存可能にする ---
        outNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeNode")
        slicer.util.updateVolumeFromArray(outNode, rgba)
        outNode.CopyOrientation(volumeNode)

        displayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVectorVolumeDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        outNode.SetAndObserveDisplayNodeID(displayNode.GetID())

        displayNode.SetDefaultColorMap()
        slicer.mrmlScene.RemoveNode(labelmapNode)

        return outNode   
    
    def closest_point(self,points, ref):
        ref = np.array(ref)
        return min(points, key=lambda p: np.linalg.norm(np.array(p) - ref))  
    def sanitize_filename(self,name):
        # Windowsで禁止されている文字を _ に置換
        return re.sub(r'[\\/:*?"<>|]', '_', name)
    
    def rasToIjkPoints(self,volumeNode, rasPoints):
        """
        rasPoints: (N,3) numpy array in RAS
        return: (N,3) numpy array in IJK (float)
        """
        rasToIjk = vtk.vtkMatrix4x4()
        volumeNode.GetRASToIJKMatrix(rasToIjk)
    
        ijkPoints = np.zeros_like(rasPoints, dtype=float)
    
        for i, p in enumerate(rasPoints):
            ijk_h = rasToIjk.MultiplyPoint([p[0], p[1], p[2], 1.0])
            ijkPoints[i] = ijk_h[:3]

        return ijkPoints
    #%% PCAT and artery segmentation calulation method
    def setupSegmentEditor(self,mergedSeg, ctNode):
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentEditorNode"
        )
        segmentEditorNode.SetAndObserveSegmentationNode(mergedSeg)
        segmentEditorNode.SetAndObserveMasterVolumeNode(ctNode)
    
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    
        return segmentEditorNode, segmentEditorWidget
    def cloneSegmentation(self,sourceSeg, newName,referenceVolume):
        newSeg = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", newName
        )
        newSeg.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolume)
        newSeg.GetSegmentation().DeepCopy(sourceSeg.GetSegmentation())
        return newSeg
    
    def subtractSegment(self,mergedSeg, ctNode, segmentIdB, segmentIdA):
        segmentEditorNode, segmentEditorWidget = self.setupSegmentEditor(
            mergedSeg, ctNode
        )
    
        segmentEditorNode.SetSelectedSegmentID(segmentIdB)
        segmentEditorNode.SetActiveEffectName("Logical operators")
    
        effect = segmentEditorWidget.activeEffect()
        if effect is None:
            raise RuntimeError("Logical operators effect not available.")
    
        effect.setParameter("Operation", "SUBTRACT")
        effect.setParameter("ModifierSegmentID", segmentIdA)
    
        effect.self().onApply()
        slicer.app.processEvents()
    
        # クリーンアップ
        segmentEditorWidget = None
        slicer.mrmlScene.RemoveNode(segmentEditorNode)
       
    def intersectSegment(self,mergedSeg, ctNode, segmentIdB, segmentIdA):
        segmentEditorNode, segmentEditorWidget = self.setupSegmentEditor(
            mergedSeg, ctNode
        )
    
        segmentEditorNode.SetSelectedSegmentID(segmentIdB)
        segmentEditorNode.SetActiveEffectName("Logical operators")
    
        effect = segmentEditorWidget.activeEffect()
        if effect is None:
            raise RuntimeError("Logical operators effect not available.")
    
        effect.setParameter("Operation", "INTERSECT")
        effect.setParameter("ModifierSegmentID", segmentIdA)
    
        effect.self().onApply()
        slicer.app.processEvents()
    
        # クリーンアップ
        segmentEditorWidget = None
        slicer.mrmlScene.RemoveNode(segmentEditorNode)
        #self.registerCaseNode(segmentEditorNode)
        
    def find_first_bifurcation(self, mergedCenterlines, coord_mm, tol):
        """
        最初の分岐点に属する branch ID のリストを返す
        """
        start_points = []
        for i in range(mergedCenterlines.GetNumberOfCells()):
            start_points.append(coord_mm[i][0])
    
        start_points = np.array(start_points)
    
        # 互いに近い start point をクラスタ化
        groups = []
        used = set()
    
        for i in range(len(start_points)):
            if i in used:
                continue
            group = [i]
            for j in range(i+1, len(start_points)):
                if np.linalg.norm(start_points[i] - start_points[j]) < tol:
                    group.append(j)
            if len(group) >= 2:
                return group  # 最初に見つかった分岐
            used.update(group)
    
        return []
    
    def classify_LAD_LCX(self, branch_ids,coord_mm):
    
        """
        LM 分岐直後の branch ID から LAD / LCX を判定（改良版）
        """
        scores = {}
         
        for bid in branch_ids:
            pts = coord_mm[bid]
            n = min(15, len(pts)-1)
         
            v = pts[n] - pts[0]
            v = v / np.linalg.norm(v)
         
            # 成分
            vx, vy, vz = v
         
            # LAD: 下向き（Z-）が強い
            lad_score = -vz
         
            # LCX: Zが小さく、XY平面に沿う + 後壁方向
            lcx_score = (1 - abs(vz)) + abs(vy)
         
            scores[bid] = (lad_score, lcx_score)
         
        lad_id = max(scores, key=lambda k: scores[k][0])
         
        # LAD 以外から LCX を選ぶ
        lcx_candidates = {k: v for k, v in scores.items() if k != lad_id}
        lcx_id = max(lcx_candidates, key=lambda k: lcx_candidates[k][1])
         
        return lad_id, lcx_id
    #LAD,LCXの場合にbifurcationを探してある程度自動で番号をふる
    def collect_until_length(self, start_id,coord_mm, mergedCenterlines,target_len=40.0, angle_th=np.deg2rad(30)):
        collected = [start_id]
        cum_len = 0.0
    
        pts_prev = coord_mm[start_id]
        v_prev = pts_prev[-1] - pts_prev[0]
        v_prev /= np.linalg.norm(v_prev)
    
        diffs = np.diff(pts_prev, axis=0)
        cum_len += np.sum(np.linalg.norm(diffs, axis=1))
    
        for i in range(start_id+1, mergedCenterlines.GetNumberOfCells()):
            pts = coord_mm[i]
            v = pts[min(10, len(pts)-1)] - pts[0]
            v /= np.linalg.norm(v)
    
            # 方向が近いものだけ継続
            if np.arccos(np.clip(np.dot(v_prev, v), -1, 1)) < angle_th:
                collected.append(i)
                diffs = np.diff(pts, axis=0)
                cum_len += np.sum(np.linalg.norm(diffs, axis=1))
                v_prev = v
    
            if cum_len >= target_len:
                break
    
        return collected
    """
    def setCaseNodeCollector(self, caseNodeIDs):
        if hasattr(self, "_caseNodeIDs"):
            return
        self._caseNodeIDs = caseNodeIDs  
        
    def registerCaseNode(self, node):
        if not node:
            return
        nid = node.GetID()
        if nid not in self._caseNodeIDs:
            self._caseNodeIDs.append(nid)
        print("logic sees:", self._caseNodeIDs)
        print("Logic self id :", id(self))
        print("Logic list id :", id(self._caseNodeIDs))
    """