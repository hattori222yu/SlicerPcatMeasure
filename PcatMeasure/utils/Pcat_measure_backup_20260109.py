# -*- coding: utf-8 -*-
"""
Created on Fri Oct 24 10:49:13 2025

@author: fight
"""
import os
import sys

currentDir = os.path.dirname(os.path.abspath(__file__))
utilsDir = os.path.join(currentDir, "utils")

if utilsDir not in sys.path:
    sys.path.insert(0, utilsDir)   # ← 先頭に入れるのが重要
import slicer
from slicer.ScriptedLoadableModule import *
import qt, ctk, vtk, os
#sys.path.append("C:/Users/Hattori/SegmentationViewer/VMTK-based-Centerline-Extraction-main")  # .py のあるフォルダ

base_dir = os.path.dirname(os.path.abspath(__file__))
vmtk_dir = os.path.join(base_dir, "VMTK-based-Centerline-Extraction-main")

sys.path.append(vmtk_dir)
import ExtractCenterline_slicer
import pickle
import numpy as np
import nibabel as nib
from nibabel.affines import apply_affine
import utils
import ExtractCenterline_slicer
#import sys
#sys.path.append("C:/Users/Hattori/SegmentationViewer")  # chk_branch.py のあるフォルダを追加
#from chk_branch import ChkBranch
utils_dir = os.path.join(base_dir, "utils")
sys.path.append(utils_dir)

#sys.path.append("C:/Users/Hattori/SegmentationViewer/utils")
from branch import showMultiCheckPopup
from cal_startpoint import cal_start_point
from save_overlay import exportSegToLabel
from save_overlay import saveOverlayImage
from save_poly import save_poly
from create_curved_cylinder_mask import create_curved_cylinder_mask
from getCTvaluesFromSegmentation import getCTvaluesFromSegmentation

from vtk.util import numpy_support
from vtk.numpy_interface import dataset_adapter as dsa
#import branch
import vtk.util.numpy_support
#
# モジュール情報クラス
#
class Pcat_measure(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Pcat measure"
        parent.categories = ["Pcat measurement"]
        parent.contributors = ["hattori"]
        parent.helpText = "pcat measure."
        parent.acknowledgementText = "Developed for PCAT project."

#
# GUI部分
#
class Pcat_measureWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        #
        # --- レイアウト ---
        #
        self.layout = qt.QVBoxLayout()

        # タイトル
        titleLabel = qt.QLabel("Pcat measure")
        titleLabel.setStyleSheet("font-weight: bold; font-size: 14px; color: #2a82da;")
        self.layout.addWidget(titleLabel)

        # ファイルパス表示用
        self.ctPathLabel = qt.QLabel("CT: No file selected.")
        self.segPathLabel = qt.QLabel("Segmentation: No file selected.")
        self.pathLabel = qt.QLabel("No file selected.")
        self.layout.addWidget(self.pathLabel)
        self.layout.addWidget(self.ctPathLabel)
        self.layout.addWidget(self.segPathLabel)

        # ボタン
        self.loadCTButton = qt.QPushButton("Load CT (file dialog)")
        self.loadCTButton2 = qt.QPushButton("[1] : Get CT Node")
        self.addPointButton = qt.QPushButton("[2] : Starting Point")
        self.loadSegButton2 = qt.QPushButton("Load Seg (file dialog)")
        self.loadSegButton3 = qt.QPushButton("[3]:Select branches")
        self.loadSegButton4 = qt.QPushButton("[4]:Analysis PCAT")
        self.loadSegButton = qt.QPushButton("test")
        self.getCoordsButton = qt.QPushButton("test2")
        self.clearButton = qt.QPushButton("Clear All")
        self.clearButton2 = qt.QPushButton("Clear (except CT)")
        self.clearButton3 = qt.QPushButton("Clear (except CT and Seg)")
        self.saveOverlayCheckBox = qt.QCheckBox("Save Overlay Images")
        self.saveOverlayCheckBox.checked = False

        self.loadCheckBox = qt.QCheckBox("From Scene(True) or dialog(False)")
        self.loadCheckBox.checked = True


        spaceLabel = qt.QLabel("         ")
        spaceLabel.setStyleSheet("font-weight: bold;")
        
        spaceLabel2 = qt.QLabel("Option")
        spaceLabel2.setStyleSheet("font-weight: bold;")
        
        spaceLabel3 = qt.QLabel("Test")
        spaceLabel3.setStyleSheet("font-weight: bold;")
        
        spaceLabel4 = qt.QLabel("Clear data")
        spaceLabel4.setStyleSheet("font-weight: bold;")
        
        # --- CT Volume selector ---
        ctLabel = qt.QLabel("Select CT Volume (from Scene)")
        ctLabel.setStyleSheet("font-weight: bold;")
        
        
        self.ctSelector = slicer.qMRMLNodeComboBox()
        self.ctSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.ctSelector.selectNodeUponCreation = False
        self.ctSelector.addEnabled = False
        self.ctSelector.removeEnabled = False
        self.ctSelector.noneEnabled = True
        self.ctSelector.setMRMLScene(slicer.mrmlScene)
        
                        
        #すでに開いているsegmentaionを使う
        self.segmentationSelector = slicer.qMRMLNodeComboBox()
        self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.segmentationSelector.selectNodeUponCreation = False
        self.segmentationSelector.addEnabled = False
        self.segmentationSelector.removeEnabled = False
        self.segmentationSelector.noneEnabled = True
        self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
        segLabel = qt.QLabel("Select Segmentation (from Scene)")
        segLabel.setStyleSheet("font-weight: bold;")
        
        # --- Segmentationからsegment名を取得する用 ---
        self.segmentSelector = slicer.qMRMLSegmentSelectorWidget()
        self.segmentSelector.setMRMLScene(slicer.mrmlScene)
        self.segmentSelector.setToolTip("Select segment to process")
        
        
        
        # --- Coronary artery selection ---
        arteryLabel = qt.QLabel("Target coronary artery")
        arteryLabel.setStyleSheet("font-weight: bold;")
        
        
        self.rcaRadio = qt.QRadioButton("RCA")
        self.ladRadio = qt.QRadioButton("LAD")
        self.LcxRadio = qt.QRadioButton("LCX")

        # デフォルト
        self.rcaRadio.setChecked(True)
        self.coronary_artery_name = "RCA"
        # ButtonGroup（重要）
        self.arteryButtonGroup = qt.QButtonGroup()
        self.arteryButtonGroup.addButton(self.rcaRadio)
        self.arteryButtonGroup.addButton(self.ladRadio)
        self.arteryButtonGroup.addButton(self.LcxRadio)

        #レイアウト
        self.layout.addWidget(spaceLabel)
        self.layout.addWidget(arteryLabel)
        self.layout.addWidget(self.rcaRadio)
        self.layout.addWidget(self.ladRadio)
        self.layout.addWidget(self.LcxRadio)

        self.layout.addWidget(spaceLabel2)
        self.layout.addWidget(self.loadCheckBox)
        self.layout.addWidget(self.saveOverlayCheckBox)
        
        self.layout.addWidget(spaceLabel)
        self.layout.addWidget(ctLabel)
        self.layout.addWidget(self.ctSelector)
        self.layout.addWidget(self.loadCTButton2)
        self.layout.addWidget(self.addPointButton)
        self.layout.addWidget(spaceLabel)

        #self.layout.addWidget(segLabel)
        #self.layout.addWidget(self.segmentationSelector)
        
        
        segLayout = qt.QHBoxLayout()
        segLayout.addWidget(segLabel)
        segLayout.addWidget(self.segmentationSelector)
        
        self.layout.addLayout(segLayout)
        self.layout.addWidget(self.segmentSelector)
                
        
        
        self.layout.addWidget(self.loadSegButton3)
        self.layout.addWidget(self.loadSegButton4)
        
        self.layout.addWidget(spaceLabel)
        self.layout.addWidget(spaceLabel4)
        self.layout.addWidget(self.clearButton)
        self.layout.addWidget(self.clearButton2)
        self.layout.addWidget(self.clearButton3)


        #self.layout.addWidget(spaceLabel)
        #self.layout.addWidget(spaceLabel2)

        #self.layout.addWidget(self.loadCTButton)
        #self.layout.addWidget(self.addPointButton)
        #self.layout.addWidget(self.loadSegButton2)

        self.layout.addWidget(spaceLabel)
        self.layout.addWidget(spaceLabel3)
        #---------------ここから下のボタンはテスト用
        self.layout.addWidget(self.loadSegButton)
        self.layout.addWidget(self.getCoordsButton)
        
        
        
        
        # シグナル接続
        #self.loadCTButton.connect("clicked(bool)", self.onLoadCT)
        self.loadCTButton2.connect("clicked(bool)", self.onLoadCT2)
        self.loadSegButton.connect("clicked(bool)", self.onLoadSegmentation)
        #self.loadSegButton2.connect("clicked(bool)", self.onLoadSegmentation2)
        self.loadSegButton3.connect("clicked(bool)", self.select_branches)
        self.loadSegButton4.connect("clicked(bool)", self.analysys_pcat)

        self.addPointButton.connect("clicked(bool)", self.onEnableMarkups)
        self.getCoordsButton.connect('clicked(bool)', self.onGetCoordinates)
        self.clearButton.clicked.connect(self.clearAllNodes)
        self.clearButton2.clicked.connect(self.clearSegNodes)
        self.clearButton3.clicked.connect(self.clearcenterlineNodes)

        self.rcaRadio.toggled.connect(self.onArteryChanged)
        self.ladRadio.toggled.connect(self.onArteryChanged)
        self.LcxRadio.toggled.connect(self.onArteryChanged)
        # Segmentation が変わったら SegmentSelector に反映
       
        self.layout.addStretch(1)
        self.parent.layout().addLayout(self.layout)
        # ノード保持用
        self.ctNode = None
        self.segNode = None
        self.seg2Node = None
        ## イベントオブザーバ用変数
        self.observerTag = None
        
        
        
        
        
    # --- ボタン押下時の動作 ---
    #
    def onLoadCT(self):
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
        except Exception as e:
            slicer.util.errorDisplay(f"Error loading CT file:\n{str(e)}")
    def onLoadCT2(self):
        import slicer
        if self.loadCheckBox.checked:
            self.ctNode = self.ctSelector.currentNode()
            if self.ctNode is None:
                slicer.util.errorDisplay("No CT Volume selected.")
                return
        
            self.ctPathLabel.setText(f"CT (Scene): {self.ctNode.GetName()}")
        
            slicer.util.setSliceViewerLayers(background=self.ctNode)
            slicer.app.layoutManager().resetSliceViews()
            slicer.app.layoutManager().resetThreeDViews()
            #print("CT Loaded")      
            # --- ここが重要 ---
            storageNode = self.ctNode.GetStorageNode()
            if storageNode and storageNode.GetFileName():
                self.ct_file_path = storageNode.GetFileName()
                self.ct_file_name = os.path.basename(self.ct_file_path)
            else:
                # Scene 内生成などの場合
                self.ct_file_path = None
                self.ct_file_name = self.ctNode.GetName()
            print("--Loaded CT")
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
                # --- ここが重要 ---
                self.ct_file_path = filePath
                self.ct_file_name = os.path.basename(filePath)
            except Exception as e:
                slicer.util.errorDisplay(f"Error loading CT file:\n{str(e)}")    
            print("--Loaded CT")
    def onArteryChanged(self):
        if self.rcaRadio.isChecked():
            self.coronary_artery_name = "RCA"
        elif self.ladRadio.isChecked():
            self.coronary_artery_name = "LAD"
        elif self.LcxRadio.isChecked():
            self.coronary_artery_name = "LCX"

        
    #   
    # --- セグメンテーション読み込み ---
    #
    
    def onLoadSegmentation(self):
        
        total_lengths = [100.0, 150.0, 200.0, 50.0]
        default_ids = [0, 2]
        
        
        selected_ids, total_selected_length = showMultiCheckPopup(
            total_lengths, default_ids, "RCA"
        )
        
        print("Selected branches:", selected_ids)
        print("Total length:", total_selected_length)
        
                
    def onClick(self,observer, eventid):
        pos = slicer.modules.markups.logic().GetActiveList().GetNthControlPointPosition(0)
        print(f"Clicked position (RAS): {pos}")
    
    def onBranchSelectionAccepted(self, selected_ids, total_selected_length):
        self.selected_ids = selected_ids
        self.total_selected_length = total_selected_length

        print("--Selected branch IDs:", self.selected_ids)
        print("--Total length:", self.total_selected_length)
    
#%% def onEnableMarkups(self):           
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
    
        #slicer.util.infoDisplay("Click on the CT image to add points. (Press Esc to stop)")
        # ---- コールバック関数 ----
#%% def onGetCoordinates(self):
    def onGetCoordinates(self):
        import slicer
    
        # Markupsノードを取得
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("PickedPoints")
        if not markupsNode:
            slicer.util.warningDisplay("No markups found. Please enable markups and place points first.")
            return
    
        n = markupsNode.GetNumberOfFiducials()
        if n == 0:
            slicer.util.warningDisplay("No points placed yet.")
            return
    
        coordinates = []
        for i in range(n):
            ras = [0.0, 0.0, 0.0]
            markupsNode.GetNthFiducialPosition(i, ras)
            coordinates.append(ras)
            print(f"Point {i+1}: R={ras[0]:.2f}, A={ras[1]:.2f}, S={ras[2]:.2f}")
    
        # 出力例：メッセージで全座標をまとめて表示
        #msg = "\n".join([f"P{i+1}: {r[0]:.2f}, {r[1]:.2f}, {r[2]:.2f}" for i, r in enumerate(coordinates)])
        #slicer.util.infoDisplay(f"Picked Points (RAS):\n{msg}")
    def distance_point_to_slice(self,pointRAS, originRAS, normalRAS):
        v = np.array(pointRAS) - np.array(originRAS)
        return abs(np.dot(v, normalRAS))
#%% def clearAllNodes(self):
    def clearAllNodes(self):
        scene = slicer.mrmlScene
    
        # === 消去したいノードの種類 ===
        removeClasses = [
            "vtkMRMLScalarVolumeNode",
            "vtkMRMLLabelMapVolumeNode",
            "vtkMRMLSegmentationNode",
            "vtkMRMLModelNode",
            "vtkMRMLMarkupsNode",
            "vtkMRMLTextNode",
            "vtkMRMLTableNode",
            "vtkMRMLVectorVolumeNode",
        ]
    
        # === 各ノードを走査して削除 ===
        nodesToRemove = []
        for className in removeClasses:
            collection = scene.GetNodesByClass(className)
            for i in range(collection.GetNumberOfItems()):
                node = collection.GetItemAsObject(i)
                nodesToRemove.append(node)
    
        # 実際に削除
        for node in nodesToRemove:
            scene.RemoveNode(node)
           
        lm = slicer.app.layoutManager()
        view = lm.threeDWidget(0).threeDView()
        renderer = view.renderWindow().GetRenderers().GetFirstRenderer()
        
        if hasattr(self, "textActors"):
            for actor in self.textActors:
                renderer.RemoveActor(actor)
            self.textActors.clear()
        
        view.renderWindow().Render()
            
            
        print("✔ All displayable nodes cleared.")
        
    def clearSegNodes(self):
        scene = slicer.mrmlScene
    
        # === 消去したいノードの種類 ===
        removeClasses = [
            
            "vtkMRMLLabelMapVolumeNode",
            "vtkMRMLSegmentationNode",
            "vtkMRMLModelNode",
            "vtkMRMLMarkupsNode",
            "vtkMRMLTextNode",
            "vtkMRMLTableNode",
            "vtkMRMLVectorVolumeNode",
        ]
    
        # === 各ノードを走査して削除 ===
        nodesToRemove = []
        for className in removeClasses:
            collection = scene.GetNodesByClass(className)
            for i in range(collection.GetNumberOfItems()):
                node = collection.GetItemAsObject(i)
                nodesToRemove.append(node)
    
        # 実際に削除
        for node in nodesToRemove:
            scene.RemoveNode(node)
           
        lm = slicer.app.layoutManager()
        view = lm.threeDWidget(0).threeDView()
        renderer = view.renderWindow().GetRenderers().GetFirstRenderer()
        
        if hasattr(self, "textActors"):
            for actor in self.textActors:
                renderer.RemoveActor(actor)
            self.textActors.clear()
        
        view.renderWindow().Render()
            
            
        print("✔ All nodes except the CT have been cleared.")    
    
    def clearcenterlineNodes(self):
        scene = slicer.mrmlScene
    
        # === 消去したいノードの種類 ===
        removeClasses = [
            
            "vtkMRMLLabelMapVolumeNode",
            "vtkMRMLModelNode",
            "vtkMRMLMarkupsNode",
            "vtkMRMLTextNode",
            "vtkMRMLTableNode",
            "vtkMRMLVectorVolumeNode",
        ]
    
        # === 各ノードを走査して削除 ===
        nodesToRemove = []
        for className in removeClasses:
            collection = scene.GetNodesByClass(className)
            for i in range(collection.GetNumberOfItems()):
                node = collection.GetItemAsObject(i)
                nodesToRemove.append(node)
    
        # 実際に削除
        for node in nodesToRemove:
            scene.RemoveNode(node)
           
        lm = slicer.app.layoutManager()
        view = lm.threeDWidget(0).threeDView()
        renderer = view.renderWindow().GetRenderers().GetFirstRenderer()
        
        if hasattr(self, "textActors"):
            for actor in self.textActors:
                renderer.RemoveActor(actor)
            self.textActors.clear()
        
        view.renderWindow().Render()
            
            
        print("✔ All nodes except the segmentation have been cleared.")    
            
#%%
    def direction_vector(self,points, n=10):
        """branch の進行方向（最初の n 点）"""
        p0 = points[0]
        p1 = points[min(n, len(points)-1)]
        v = p1 - p0
        norm = np.linalg.norm(v)
        if norm < 1e-6:
            return np.zeros(3)
        return v / norm


    def angle_between(self,v1, v2):
        import math
        """2ベクトルのなす角（rad）"""
        dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
        return math.acos(dot)
    def estimate_LAD_LCX_branches(self, heart_center):
        """
        self.coord_mm
        self.mergedCenterlines
        self.total_lengths を使って
        LAD / LCX の branch ID リストを返す
        """
    
        MIN_LENGTH = 20.0   # mm
        ANGLE_TH = np.deg2rad(30)
    
        total_lengths = []
        for i in range(self.mergedCenterlines.GetNumberOfCells()):
            pts = self.coord_mm[i]
            diffs = np.diff(pts, axis=0)
            total_lengths.append(np.sum(np.linalg.norm(diffs, axis=1)))
    
        # --- 有効 branch（短すぎる枝を除外）
        valid_ids = [i for i, L in enumerate(total_lengths) if L > MIN_LENGTH]
    
        lad_scores = []
        lcx_scores = []
    
        for i in valid_ids:
            pts = self.coord_mm[i]
            v = self.direction_vector(pts)
    
            delta_z = pts[-1,2] - pts[0,2]
    
            r0 = np.linalg.norm(pts[0] - heart_center)
            r1 = np.linalg.norm(pts[-1] - heart_center)
            delta_r = r1 - r0
    
            length_score = total_lengths[i] / max(total_lengths)
    
            # --- LAD スコア
            lad_score = (
                2.0 * max(0, -v[2]) +          # 下方向
                1.5 * max(0, -delta_z / 30) +  # Z低下
                0.5 * length_score
            )
    
            # --- LCX スコア
            lcx_score = (
                2.0 * max(0, -v[0]) +          # 左外側
                1.5 * max(0, delta_r / 20) +
                0.5 * length_score
            )
    
            lad_scores.append((lad_score, i))
            lcx_scores.append((lcx_score, i))
    
        lad_root = max(lad_scores)[1]
        lcx_root = max(lcx_scores)[1]
    
        # --- 連続 branch を追加
        def collect_continuous(root_id):
            collected = [root_id]
            v_prev = self.direction_vector(self.coord_mm[root_id])
    
            for j in range(root_id+1, self.mergedCenterlines.GetNumberOfCells()):
                if j not in valid_ids:
                    continue
                v_next = self.direction_vector(self.coord_mm[j])
                if self.angle_between(v_prev, v_next) < ANGLE_TH:
                    collected.append(j)
                    v_prev = v_next
                else:
                    break
            return collected
    
        lad_branches = collect_continuous(lad_root)
        lcx_branches = collect_continuous(lcx_root)
    
        return lad_branches, lcx_branches
    def find_first_bifurcation(self, tol=1.0):
        """
        最初の分岐点に属する branch ID のリストを返す
        """
        start_points = []
        for i in range(self.mergedCenterlines.GetNumberOfCells()):
            start_points.append(self.coord_mm[i][0])
    
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
    
    def classify_LAD_LCX(self, branch_ids):
        """
        分岐直後の branch ID から LAD / LCX を判定．最初の判別コード．LADは割とうまくいくか・・・？
        
        scores = {}
    
        for bid in branch_ids:
            pts = self.coord_mm[bid]
            v = pts[min(10, len(pts)-1)] - pts[0]
            v = v / np.linalg.norm(v)
    
            lad_score = -v[2]          # 下向き
            lcx_score = -v[0]          # 左外側
    
            scores[bid] = (lad_score, lcx_score)
    
        lad_id = max(scores, key=lambda k: scores[k][0])
        lcx_id = max(scores, key=lambda k: scores[k][1])
    
        return lad_id, lcx_id
        """
    
        """
        LM 分岐直後の branch ID から LAD / LCX を判定（改良版）
        """
        scores = {}
         
        for bid in branch_ids:
            pts = self.coord_mm[bid]
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
    
    
    def collect_until_length(self, start_id, target_len=40.0, angle_th=np.deg2rad(30)):
        collected = [start_id]
        cum_len = 0.0
    
        pts_prev = self.coord_mm[start_id]
        v_prev = pts_prev[-1] - pts_prev[0]
        v_prev /= np.linalg.norm(v_prev)
    
        diffs = np.diff(pts_prev, axis=0)
        cum_len += np.sum(np.linalg.norm(diffs, axis=1))
    
        for i in range(start_id+1, self.mergedCenterlines.GetNumberOfCells()):
            pts = self.coord_mm[i]
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
#%% PCAT and artery seg cal
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
    def cloneSegmentation(self,sourceSeg, newName):
        newSeg = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", newName
        )
        newSeg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
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
        
        
#%% def onLoadSegmentation3(self):
    def closest_point(self,points, ref):
        ref = np.array(ref)
        return min(points, key=lambda p: np.linalg.norm(np.array(p) - ref))  
    def select_branches(self):
        print("step0:Analysis target =", self.coronary_artery_name)
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
                
                
        
        case_id = '00000000'
        #segmentName = 'Segment_1'
        targetClass="left"
        
        endpointName = f"Endpoints_{case_id}_{targetClass}"
        endpointmodelName = f"Endptmodel_{case_id}_{targetClass}"
        centermodelName = f"Model_{case_id}_{targetClass}"
        voronoimodelName = f"Voronoi_{case_id}_{targetClass}"
        centertableName = f"Properties_{case_id}_{targetClass}"
        centercurveName = f"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      _"
        
        # 保存先フォルダ
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.save_dir_output=os.path.join(base_dir,"output")
        # フォルダがなければ作成
        os.makedirs(self.save_dir_output, exist_ok=True)
        self.save_dir=os.path.join(self.save_dir_output,self.ct_file_name)
        self.save_dir=self.save_dir.replace(".","_")
        os.makedirs(self.save_dir, exist_ok=True)
        # ファイルパス
        save_path = os.path.join(self.save_dir, "01_inputSurfacePolyData.vtk")
        
        
        # Slicer add node
        endpointModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", endpointmodelName)
        centerlineModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", centermodelName)
        voronoiModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", voronoimodelName)
        centerlinePropertiesTableNode =  slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode" ,centertableName)
        centerlineCurveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", centercurveName)
        
        #球体を非表示
        #centerlineCurveNode.GetDisplayNode().SetVisibility(False)

        # Step1: Load Segmentation: From Path to 'vtkMRMLSegmentationNode' type        
        print("step1:Load Segmentation")
      
       
        #seg_path=filePath
        #segmentationNode = slicer.util.loadSegmentation(seg_path)
        #segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
        if self.loadCheckBox.checked:
            self.segmentationNode = self.segmentationSelector.currentNode()
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
            
        ##############################coronarycenterlineからセグメンテーションを受け取ったかのデバッグ用
        
        if self.loadCheckBox.checked:
            segmentationNode_debag = self.segmentationSelector.currentNode()
        else:
            segmentationNode_debag = slicer.util.loadSegmentation(filePath)
        
        # Step2: validation
        segmentID_debag, surfacePolyData_debag = self.validateSegmentationNode(
            segmentationNode_debag,
            segmentName= self.segmentationNode.GetSegmentation().GetSegment(segmentID).GetName()

        )
        
        if segmentID_debag is None:
            print(" segmentID is None")
            return  
        
        print("✅ Segmentation surface points:", surfacePolyData_debag.GetNumberOfPoints())
        ################################
        
        
        #from vmtk.ExtractCenterline import ExtractCenterline
        extractLogic = ExtractCenterline_slicer.ExtractCenterlineLogic()

        # Step2: SegmentationNode to vtkPolyData
        print("step2:SegmentationNode to vtkPolyData")
        inputSurfacePolyData = extractLogic.polyDataFromNode(self.segmentationNode, segmentID)
        #print('DEBUG', inputSurfacePolyData)
        SAVE_VTK=True
        save_poly(SAVE_VTK, inputSurfacePolyData, os.path.join(self.save_dir, f"01_inputSurfacePolyData_{self.coronary_artery_name}.vtk"))
                 
               
        
        targetNumberOfPoints = 5000.0
        decimationAggressiveness = 4 # I had to lower this to 3.5 in at least one case to get it to work, 4 is the default in the module
        subdivideInputSurface = False
        
        if inputSurfacePolyData.GetNumberOfPoints() == 0:
            slicer.util.errorDisplay("Input surface is empty")
            return
        preprocessedPolyData = extractLogic.preprocess(inputSurfacePolyData, targetNumberOfPoints, decimationAggressiveness, subdivideInputSurface)
        save_poly(SAVE_VTK, preprocessedPolyData, os.path.join(self.save_dir, f"02_preprocessedPolyData_{self.coronary_artery_name}.vtk"))
        
        # Step3: Extract Centerline Network (Approximated Centerline)
        print("step3:Extract Centerline Network")
        endPointsMarkupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", endpointName)
        #非表示
        endPointsMarkupsNode.GetDisplayNode().SetVisibility(False)
        networkPolyData = extractLogic.extractNetwork(preprocessedPolyData, endPointsMarkupsNode, computeGeometry=True)  # Voronoi 
        # Create Centerline Model
        endpointModelNode.SetAndObserveMesh(networkPolyData)

        # Step4: Get EndPoints ( AutoDetect )
        print("step4:Get EndPoints")
        #startPointPosition=None
        
        startPointPosition_list = []
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("PickedPoints")

        n = markupsNode.GetNumberOfControlPoints()
        for i in range(n):
            ras = [0.0, 0.0, 0.0]
            markupsNode.GetNthControlPointPositionWorld(i, ras)  # ★重要
            startPointPosition_list.append(ras)
        #startPointPosition = startPointPosition_list[0]
        #初期値
        aortaCenter = [0, 0, 0]
        #複数マークアップがある場合に一番近い点を取得
        startPointPosition = self.closest_point(startPointPosition_list, aortaCenter)
        print("startPointPosition:",startPointPosition)

        endpointPositions = extractLogic.getEndPoints(networkPolyData, startPointPosition) # AutoDetect the endpoints. type: List
        print("Endposition:",endpointPositions)
        
        endPointsMarkupsNode.RemoveAllControlPoints()
        for position in endpointPositions:
            endPointsMarkupsNode.AddControlPoint(vtk.vtkVector3d(position))

        # Step5: Extract Centerline, Voronoi
        print("step5:Get Extract Centerline, Voronoi")
        centerlinePolyData, voronoiDiagramPolyData = extractLogic.extractCenterline(preprocessedPolyData, endPointsMarkupsNode)
        centerlineModelNode.SetAndObserveMesh(centerlinePolyData)          
        voronoiModelNode.SetAndObserveMesh(voronoiDiagramPolyData)  

        # Step6: Extract centerlineCurves
        print("step6:Extract centerlineCurves")
        self.mergedCenterlines, centerlineProperties, self.cell_pt = extractLogic.createCurveTreeFromCenterline(centerlinePolyData, centerlineCurveNode, centerlinePropertiesTableNode) 
            
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
        print("step7:Extract and save centerlineCurve info")
        SAVE_INFO = True
        if(SAVE_INFO):
            r1 = self.mergedCenterlines.GetPointData().GetArray('Radius')
            
            self.radius_arr = vtk.util.numpy_support.vtk_to_numpy(r1)    
            
            
            with open(os.path.join(self.save_dir,f'00_centerCurve_radius_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.radius_arr, f, pickle.HIGHEST_PROTOCOL)

            properties_dict = {}
            for columnName in [extractLogic.lengthArrayName, extractLogic.curvatureArrayName, extractLogic.torsionArrayName, extractLogic.tortuosityArrayName]:
                vtk_arr = centerlineProperties.GetPointData().GetArray(columnName)
                properties_dict[columnName] = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            with open(os.path.join(self.save_dir,f'00_centerCurve_property_dict_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(properties_dict, f, pickle.HIGHEST_PROTOCOL)
                
            #print(cell_pt)
            with open(os.path.join(self.save_dir,f'00_centerCurve_cell_idx_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.cell_pt, f, pickle.HIGHEST_PROTOCOL)

            vtk_arr = self.mergedCenterlines.GetPoints().GetData()
            array = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            self.coord_mm = {}
            self.coord_voxel = {}
            for cell in self.cell_pt:
                cell_array = array[self.ce_ll_pt_LIST[cell]]
                self.coord_mm[cell] = cell_array
                self.coord_voxel[cell] = apply_affine(np.linalg.inv(affine), array[self.cell_pt[cell]])
            with open(os.path.join(self.save_dir,f'00_centerCurve_coord_mm_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.coord_mm, f, pickle.HIGHEST_PROTOCOL)
            with open(os.path.join(self.save_dir,f'00_centerCurve_coord_voxel_{self.coronary_artery_name}.pickle'), 'wb') as f:
                pickle.dump(self.coord_voxel, f, pickle.HIGHEST_PROTOCOL)

        print("step8:Auto get branch IDs")
        groupIdsArrayName = 'GroupIds'
        groupIdsArray = self.mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
    
        # 2. ユニークな GroupIds を取得
        uniqueGroupIds = list(set(groupIdsArray.GetTuple1(i) for i in range(groupIdsArray.GetNumberOfTuples())))
        #print("uG",uniqueGroupIds)
        #uniqueGroupIds.sort()  # 一応順番揃える
        numGroups = len(uniqueGroupIds)
        
        
        
        #get branch
        self.default_branch_id= []

        total_lengths = []
        for i in range(self.mergedCenterlines.GetNumberOfCells()):
            
            points_branch = self.coord_mm[i]  # shape = (N, 3)            
            diffs = np.diff(points_branch, axis=0)
            segment_lengths = np.linalg.norm(diffs, axis=1)
            total_length = np.sum(segment_lengths)
            #print("i",i,"total_length",total_length)
            total_lengths.append(total_length)
        #self.coronary_artery_name="RCA"
        
        
        
        """
        # 心臓中心（簡易：CT volume 中心）
        dims = self.ctNode.GetImageData().GetDimensions()
        spacing = self.ctNode.GetSpacing()
        origin = self.ctNode.GetOrigin()
        
        heart_center = np.array([
            origin[0] + dims[0]*spacing[0]/2,
            origin[1] + dims[1]*spacing[1]/2,
            origin[2] + dims[2]*spacing[2]/2
        ])
        
        lad_ids, lcx_ids = self.estimate_LAD_LCX_branches(heart_center)
        print("test",lad_ids, lcx_ids)
        """
        
        if self.coronary_artery_name in ("LAD", "LCX"):
            #print(self.coronary_artery_name,"nanndeeeeeeeeeee")
            bifurcation_ids = self.find_first_bifurcation()
            #print("first bifurcation_ids",bifurcation_ids)
            if len(bifurcation_ids) < 2:
                raise RuntimeError("LM bifurcation not found")
            
            lcx_root, lad_root = self.classify_LAD_LCX(bifurcation_ids)
            
        if self.coronary_artery_name == "RCA":
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                self.default_branch_id.append(i)
                if cumulative_length >= 50:
                    break
        elif self.coronary_artery_name=="LAD":
            
            self.default_branch_id = self.collect_until_length(lad_root, 40.0)
        elif self.coronary_artery_name=="LCX":
            self.default_branch_id = self.collect_until_length(lcx_root, 40.0)
        #branch_id はとりあえず自動で選んだPCAT領域に対応するID
        
        print("--get branch ID is ",self.default_branch_id)
        
        
        
        #CT画像上で取得した起始部の座標を取得###################################################
        
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
            print(f"--start point {i+1}: R={ras[0]:.2f}, A={ras[1]:.2f}, S={ras[2]:.2f}")
    
        # 出力例：メッセージで全座標をまとめて表示
        #msg = "\n".join([f"P{i+1}: {r[0]:.2f}, {r[1]:.2f}, {r[2]:.2f}" for i, r in enumerate(coordinates)])
        #slicer.util.infoDisplay(f"Picked Points (RAS):\n{msg}")
        
        ##########################################################
    
    
    
        
        ##############元のコードから．長さとかIDを表示   VIL=>view_id_lengthの略
        group_ids = self.mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
        #print("group_ids",group_ids)
        points = self.mergedCenterlines.GetPoints()
        vivid_colors = [(1, 0, 0),(0, 1, 0),(0, 0, 1),(1, 1, 0),(1, 0, 1),(0, 1, 1),(1, 0.5, 0),(0.5, 0, 1),
                         (1, 0, 0.5),(0.5, 0.5, 0),(0, 0.5, 1),(0, 1, 0.5),(0.5, 1, 0), (1, 0.25, 0),(0.25, 0, 1),
                        (0, 1, 0.25),(0.75, 0, 1),(1, 0, 0.75),(0.5, 1, 1),(1, 1, 0.5)]
        if not hasattr(self, "textActors"):
                self.textActors = []
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
                        
            
            ######################2D表示###################################################3
            """
            textActor2D = vtk.vtkTextActor()
            textActor2D.SetInput(f"{branch_id_VIL} [{total_length_VIL:.1f} mm]")
            
            textProp = textActor2D.GetTextProperty()
            textProp.SetFontSize(18)
            textProp.SetColor(vivid_colors[i])
            textProp.SetBold(True)
            textProp.SetJustificationToLeft()
            textProp.SetVerticalJustificationToBottom()
            
            # 画面左下からの位置（px）
            textActor2D.SetDisplayPosition(20, 30 + 25*i)   
            lm = slicer.app.layoutManager()
            for viewName in ["Red", "Yellow", "Green"]:  # Axial / Sagittal / Coronal
                sliceWidget = lm.sliceWidget(viewName)
                renderer = sliceWidget.sliceView().renderWindow().GetRenderers().GetFirstRenderer()
                renderer.AddActor2D(textActor2D)
                sliceWidget.sliceView().scheduleRender()
            if not hasattr(self, "sliceTextActors"):
                self.sliceTextActors = []
            self.sliceTextActors.append(textActor2D)                                        
            """
            ###################################################テスト
            
            
            
        #enabled, selected = chk_branch.showRadioPopup(total_lengths,branch_id,self.coronary_artery_name)    
        #print("enabled",enabled,"select",selected)
        print("step9:check branch")
    
        #self.selected_ids, total_selected_length = showMultiCheckPopup(total_lengths,self.branch_id,self.coronary_artery_name)
        self.selected_ids = []
        self.total_selected_length = 0.0
            
        
        displayNode = self.segmentationNode.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility3D(False)
        
        
        
        showMultiCheckPopup(
            total_lengths,
            default_ids=self.default_branch_id,
            coronary_name=self.coronary_artery_name,
            onAcceptedCallback=self.onBranchSelectionAccepted
        )
        
        
        
        #print("Selected branches:", selected_ids,"Total length:", total_selected_length,"now artery is ",self.coronary_artery_name,"coordiante",coordinates[0])
        #print("coordiante",coordinates[0][0],coordinates[0][1],coordinates[0][2])
        ####################################################################
        #どこを起始部とするかの座標をGUIとかで取得→それがpoints_culmulative_voxelで一番近い座標を探索→、それが配列で何番目かのインデックスか
        #調べて,points_culmulative_mmのほうに値としていれる→実装しました。
        ####################################################################
        #print("now cal start point ")
        
        
    def analysys_pcat(self):
        #print("Selected branch IDs:", self.selected_ids)
        #print("Total length:", self.total_selected_length)
        #selecetedIDSで選んだbrannchのcenterlineの座標を連結
        points_culmulative_mm =  np.concatenate([self.coord_mm[i] for i in self.selected_ids], axis=0)#coord_mm[self.branch_id]  # shape = (N, 3)
        points_culmulative_voxel =  np.concatenate([self.coord_voxel[i] for i in self.selected_ids], axis=0)#coord_voxel[self.branch_id]  # shape = (N, 3)
        print("points_culmulative_mm",points_culmulative_mm)
        #[abs(x) for x in coordinates[0]]でマイナスの値を絶対値化⇒したらだめでした．
        #[203,365,132]
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
        #print("RAS",ras_point)
        #199 365 130
        #print("IJK",ijk_int)
        #RAS [-13.794045901639343, 204.43605245901637, 104.45000076293945]
        #IJK [199, 367, 130]
        #RAS 形式
        #start_corrdinate=cal_start_point(coordinates[0],points_culmulative_voxel) 
        
        #IJK　形式
        start_corrdinate=cal_start_point(ijk_int,points_culmulative_voxel)
        
        print("start_corrdinate",start_corrdinate)
        
        #print("test",points_culmulative_voxel[start_corrdinate:,:])
        ##2行目はテスト
        
        points_culmulative=points_culmulative_mm[start_corrdinate:,:]
        #points_culmulative=points_culmulative_mm[10:,:]
        print("points_culmulative",points_culmulative)

       

        # 各点の差分ベクトル（連続する点の移動）
        diffs_culmulative = np.diff(points_culmulative, axis=0)  # (N-1, 3)

        # 各区間の長さ（ユークリッド距離）
        segment_lengths_culmulative = np.linalg.norm(diffs_culmulative, axis=1)  # (N-1,)

        # 累積距離の配列：先頭に0を付けて [0, d1, d1+d2, ...]
        cumulative_distances = np.insert(np.cumsum(segment_lengths_culmulative), 0, 0.0)  # shape = (N,)
        
        if self.coronary_artery_name=="RCA":
            print("mask_PCAT = (cumulative_distances >= 10.0) & (cumulative_distances <= 50.0)")
            mask_PCAT = (cumulative_distances >= 10.0) & (cumulative_distances <= 50.0)
            
        else:
            print("mask_PCAT = (cumulative_distances >= 10.0) & (cumulative_distances <= 50.0)")
            mask_PCAT = (cumulative_distances >= 0.0) & (cumulative_distances <= 40.0)
            #(155,0)
        # まず各branchのpoint idリストを順番に取り出して
        
        lists = [self.ce_ll_pt_LIST[bid] for bid in self.selected_ids]
        print("self.selected_ids",self.selected_ids)
        # それらをまとめて1次元のnumpy配列にする
        #point_ids = np.array(self.cell_pt[self.branch_id])  # 　←だとself.branch_idはリストなのでエラー
        point_ids = np.array([pid for sublist in lists for pid in sublist])  # 　←だと分岐のところの点が重複している。多分重複はよくなさそう       
        
        #####################################################################    いるかふめい
        #① VTKの点群データと累積長さを取得
        #reader = vtk.vtkPolyDataReader()
        #reader.SetFileName('C:/Users/Hattori/SegmentationViewer/output/06_mergedCenterlines.vtk')
        #reader.Update()
        #mergedCenterlines = reader.GetOutput()
        points_vtk_array = self.mergedCenterlines.GetPoints().GetData()
        self.points_np = vtk.util.numpy_support.vtk_to_numpy(points_vtk_array)
        
        point_ids_after_start_selected_=point_ids[start_corrdinate:]
        
        

        print("mask_PCAT",mask_PCAT)
        # ③ 区間を絞る（10〜20mm）
        ###########################################
        selected_ids2 = point_ids_after_start_selected_[mask_PCAT]


        #print("selected_ids",selected_ids)
        #print("冠動脈:",str(self.coronary_artery_name),"の選ばれたID",selected_ids[0],"-",selected_ids[-1])
        #cumulative_distance_maskはただprintするためだけの変数
        cumulative_distance_mask=cumulative_distances[mask_PCAT]
        print(selected_ids2)
        if selected_ids2.shape[0] < 2:
            raise ValueError("need two point data")
            
        ############################################
        # ④ 新しい vtkPoints と polyLine を作る
        ############################################
        new_points = vtk.vtkPoints()
        new_lines = vtk.vtkCellArray()
                             
        ############################################
        #print("最終的に抽出した点の数(10-50mm or 0-40mmの範囲)",selected_ids.shape)                     
        # ⑤ 点を登録
        ############################################
        id_map = {}  # 元のpoint_id → 新しい順番
        for i, pid in enumerate(selected_ids2):
            #print(i,pid)
            coord = self.points_np[pid]
            new_points.InsertNextPoint(coord)
            id_map[pid] = i    
            
        # ⑥ polyline作成（直線的な連続接続）
        ############################################
        line = vtk.vtkPolyLine()
        line.GetPointIds().SetNumberOfIds(len(selected_ids2))
        for i in range(len(selected_ids2)):
            line.GetPointIds().SetId(i, i)
        new_lines.InsertNextCell(line)
        ############################################
        # ⑦ vtkPolyData に登録
        ############################################
        self.new_polydata = vtk.vtkPolyData()
        self.new_polydata.SetPoints(new_points)
        self.new_polydata.SetLines(new_lines)
        ############################################
        # ⑧ vtkとPCATを測定する範囲をvtkとして保存
        ############################################
        writer = vtk.vtkPolyDataWriter()
        if self.coronary_artery_name=="RCA":

            writer.SetFileName(os.path.join(self.save_dir,f"04_branch{self.selected_ids}_{self.coronary_artery_name}_10to50mm.vtk"))
        else:
            writer.SetFileName(os.path.join(self.save_dir,f"04_branch{self.selected_ids}_{self.coronary_artery_name}_0to40mm.vtk"))
        writer.SetInputData(self.new_polydata)
        writer.Write()
        
        ##################################################################################################################################
        #　ここからextract pcat2
        ##################################################################################################################################
        #radius_arr=>radius_data
        #cell_pt=>cell_id_data
        print("step10:create artery & PCAT")
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
        #print(create_curved_cylinder_mask)
        import inspect
        #print(inspect.getfile(create_curved_cylinder_mask))
        tube_polydata = create_curved_cylinder_mask(branch_0_coords_PCAT, branch_0_radius_PCAT*3.0)
        print("--Tube Points(not zero):", tube_polydata.GetNumberOfPoints())  # ← 0でないこと
        if tube_polydata.GetNumberOfPoints() == 0:
            raise ValueError("Tube Points zero")
            
        #vtk_image_1x = self.polydata_to_mask2(tube_polydata, self.spacing, self.origin, self.image_size)
        #self.save_vtk_image_as_nifti(vtk_image_1x, self.spacing, self.origin, f"./{self.SAVE_PATH}/pcat_mask_new.nii.gz")
        
        # 書き出し
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(os.path.join(self.save_dir,f"05_{self.coronary_artery_name}_PCAT_Coronary_Wall.vtk"))
        writer.SetInputData(tube_polydata)
        writer.Write()
        
        
        
        print("step11:extract PCAT area")
        #######################################
        
        # tube_polydata は RAS 座標の PolyData
        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        modelNode.SetAndObservePolyData(tube_polydata)
        modelNode.SetName("seg_artery_PCAT")
        
        
        segNode_artery_PCAT = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "TubeSegmentation")
        # セグメンテーションの座標系を CT と合わせる（RAS）
        segNode_artery_PCAT.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        # モデルをセグメントとして追加
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(
            modelNode, segNode_artery_PCAT
            )         
        ##ここまでOK!
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
        #print("Exported seg_artery ->", labelA.GetName(), labelA.GetID())
        
        # 3) B -> LabelMap にエクスポート
        labelB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        try:
            logic.ExportAllSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)
        except Exception:
            logic.ExportVisibleSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)
        #print("Exported segNode_artery_PCAT ->", labelB.GetName(), labelB.GetID())

        logic.ImportLabelmapToSegmentationNode(labelA, mergedSeg)
        #print("Imported labelA into mergedSeg")
        seg = mergedSeg.GetSegmentation()
        segmentIdA = seg.GetNthSegmentID(seg.GetNumberOfSegments() - 1)

        # 5) labelB を mergedSeg に import
        logic.ImportLabelmapToSegmentationNode(labelB, mergedSeg)
        #print("Imported labelB into mergedSeg")
        segmentIdB = seg.GetNthSegmentID(seg.GetNumberOfSegments() - 1)

        # 6) 確認：mergedSeg の segment list を表示
        
        ids = seg.GetSegmentIDs()
        print("Merged segments:")
        for sid in ids:
            print("  ID:", sid, "Name:", seg.GetSegment(sid).GetName())
        
        
        
        
        
        
        
        #segmentID = mergedSeg.currentSegmentID()
        #segmentIdA=segmentID.GetSegmentation().GetSegment(segmentID).GetName()
        
        #segmentIdA = str(seg.GetSegment(0).GetName()) #"__tmp_cylinder_model__"          # artery
        #segmentIdB = str(seg.GetSegment(1).GetName()) #"seg_artery_PCAT"    # PCAT
        print("segmentIdA,B",segmentIdA,segmentIdB)
        workSeg_sub = self.cloneSegmentation(mergedSeg, "work_PCAT_subtract")
        #####################################segmentIdAに入力するためのちぇっっくよう
        segtest = workSeg_sub.GetSegmentation()

        print("=== Segments in workSeg_sub ===")
        for i in range(segtest.GetNumberOfSegments()):
            segIdtest = segtest.GetNthSegmentID(i)
            segNametest = segtest.GetSegment(segIdtest).GetName()
            print(f"{i}: ID={segIdtest}, Name={segNametest}")
        #################################
        
        self.subtractSegment(
            workSeg_sub,
            self.ctNode,
            segmentIdB,
            segmentIdA
        )
        
        PCAT_seg = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "PCAT_seg"
        )
        PCAT_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        labelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "tempLabel_sub"
        )
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
            workSeg_sub,
            [segmentIdB],
            labelNode,
            self.ctNode
        )
        
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            PCAT_seg
        )
        
        # cleanup
        slicer.mrmlScene.RemoveNode(labelNode)
        slicer.mrmlScene.RemoveNode(workSeg_sub)
        
        workSeg_int = self.cloneSegmentation(mergedSeg, "work_PCAT_intersect")
        self.intersectSegment(
            workSeg_int,
            self.ctNode,
            segmentIdB,
            segmentIdA
        )
        
        PCAT_artery_seg = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "PCAT_artery_seg"
        )
        PCAT_artery_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        labelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "tempLabel_int"
        )
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
            workSeg_int,
            [segmentIdB],
            labelNode,
            self.ctNode
        )
        
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            PCAT_artery_seg
        )
        
        # cleanup
        slicer.mrmlScene.RemoveNode(labelNode)
        slicer.mrmlScene.RemoveNode(workSeg_int)
                
                
        
        """
        segmentIdA = "Segment_1"
        segmentIdB = "seg_artery_PCAT"
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorNode.SetAndObserveSegmentationNode(mergedSeg)
        segmentEditorNode.SetAndObserveMasterVolumeNode(self.ctNode)
        
        
        
        
        
        
        # SUBTRACT 設定
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        
              
        
        
        # —— SUBTRACT: B − A ——
        segmentEditorNode.SetSelectedSegmentID(segmentIdB)
        segmentEditorNode.SetActiveEffectName("Logical operators")
        
        effect = segmentEditorWidget.activeEffect()
        if effect is None:
            raise RuntimeError("Logical operators effect not available.")
        
        effect.setParameter("Operation", "SUBTRACT")
        effect.setParameter("ModifierSegmentID", segmentIdA)
        
        # APPLY
        effect.self().onApply()
        slicer.app.processEvents()
        
        # クリーンアップ
        segmentEditorWidget = None
        #print("After SUBTRACT:")
        #for i in range(seg.GetNumberOfSegments()):
        #    segID = seg.GetNthSegmentID(i)
        #    print(" ", segID, " -> ", seg.GetSegment(segID).GetName())
            
        #############################################################ここまでOK!
        
        
        PCAT_seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "PCAT_seg")
        PCAT_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        
        
        # ---- 3) segment → labelmap ----
        labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "tempLabel")
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
            mergedSeg,              # source segmentation
            [segmentIdB],           # segment ID list
            labelNode,              # target labelmap
            self.ctNode             # reference volume
        )
        
        # ---- 4) labelmap → 新しい segmentation へインポート ----
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            PCAT_seg
        )
        """
        #print("PCAT_seg created with segment:", segmentIdB)
        
        
        # ---- 5) 不要な labelNode を削除 ----
        slicer.mrmlScene.RemoveNode(labelA)
        slicer.mrmlScene.RemoveNode(labelB)
        slicer.mrmlScene.RemoveNode(labelNode)
        slicer.mrmlScene.RemoveNode(mergedSeg)
        displayNode = segNode_artery_PCAT.GetDisplayNode()
              
        if displayNode:
            displayNode.SetVisibility(False)   
        
        segmentationdisp = PCAT_seg.GetSegmentation()
        segmentIDdisp = segmentationdisp.GetNthSegmentID(0)  # or segmentation.GetSegmentIdBySegmentName("PCAT")
        segmentdisp = segmentationdisp.GetSegment(segmentIDdisp)
        segmentdisp.SetColor(1.0, 0.0, 0.0)   # あか   
        
        
        segmentationdisp2 = PCAT_artery_seg.GetSegmentation()
        segmentIDdisp2 = segmentationdisp2.GetNthSegmentID(0)
        # or segmentation.GetSegmentIdBySegmentName("PCAT")
        segmentdisp2 = segmentationdisp2.GetSegment(segmentIDdisp2)
        segmentdisp2.SetColor(0.0, 0.0, 1.0)
        
        print("step12:cal PCAT value")
        ct_values,PCAT_value_list,PCAT_value = getCTvaluesFromSegmentation(PCAT_seg, self.ctNode,self.ct_file_path,self.coronary_artery_name,self.save_dir_output,ijk_int)
        """
        hu_min = -190
        hu_max = -30
        
        # ct_values はセグメント内ボクセルの HU 値が入った 1D numpy 配列
        masked_values = ct_values[(ct_values >= hu_min) & (ct_values <= hu_max)]
        
        if masked_values.size == 0:
            mean_hu = None   # 該当値がない場合
        else:
            mean_hu = masked_values.mean()
        """
        print("--PCAT HU:", PCAT_value)
   
    
   
        pcatLabelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            "PCAT_labelmap"
        )
        # export
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
            PCAT_seg,
            pcatLabelNode
        )
       
        # ★ 中身チェック（重要）
        imageData = pcatLabelNode.GetImageData()
        if imageData is None or imageData.GetPointData().GetScalars() is None:
            raise RuntimeError("PCAT labelmap is empty")
       
        #print("--LabelMap range:", imageData.GetScalarRange())
       
        # ---- save ----
        ok = slicer.util.saveNode(pcatLabelNode, os.path.join(self.save_dir,f"07_pcat_{self.coronary_artery_name}.nii.gz"))
        #print("--Saved to:", os.path.join(self.save_dir,f"pcat_{self.coronary_artery_name}.nii.gz"))
        
        
        
        
        
        
        
        pcatarteryLabelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            "PCAT_artery_labelmap"
        )
        # export
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
            PCAT_artery_seg,
            pcatarteryLabelNode
        )
       
        # ★ 中身チェック（重要）
        imageData2 = pcatarteryLabelNode.GetImageData()
        if imageData2 is None or imageData2.GetPointData().GetScalars() is None:
            raise RuntimeError("PCAT artry labelmap is empty")
       
        #print("--LabelMap range:", imageData2.GetScalarRange())
       
        # ---- save ----
        ok = slicer.util.saveNode(pcatarteryLabelNode, os.path.join(self.save_dir,f"06_artery_analysis_range_{self.coronary_artery_name}.nii.gz"))
        #print("--Save result:", ok)
        #print("--Saved to:", os.path.join(self.save_dir,f"artery_analysis_range_{self.coronary_artery_name}.nii.gz"))
        
        
        
        
        
        slicer.mrmlScene.RemoveNode(pcatLabelNode)

        
        
        
        
        
        if self.saveOverlayCheckBox.checked:
            overlay_dir = os.path.join(self.save_dir, "overlay")
            os.makedirs(overlay_dir, exist_ok=True)
            
            print("now save overlay")
            labelNode = exportSegToLabel(PCAT_seg, self.ctNode)
            
            saveOverlayImage(
                self.ctNode,
                labelNode,
                outputDir=overlay_dir
            )
            
   #%% デバッグ用コード．         
    def validateSegmentationNode(self, segmentationNode, segmentName=None):
        import slicer, vtk
    
        if segmentationNode is None:
            slicer.util.errorDisplay("SegmentationNode is None")
            return None, None
    
        segmentation = segmentationNode.GetSegmentation()
        if segmentation.GetNumberOfSegments() == 0:
            slicer.util.errorDisplay("Segmentation has no segments")
            return None, None
    
        # segment ID
        if segmentName:
            segmentId = segmentation.GetSegmentIdBySegmentName(segmentName)
            if not segmentId:
                slicer.util.errorDisplay(f"Segment '{segmentName}' not found")
                return None, None
        else:
            segmentId = segmentation.GetNthSegmentID(0)
    
        # Closed surface 取得
        polyData = vtk.vtkPolyData()
        ok = slicer.modules.segmentations.logic().GetSegmentClosedSurfaceRepresentation(
            segmentationNode,
            segmentId,
            polyData
        )
    
        if (not ok) or polyData.GetNumberOfPoints() == 0:
            slicer.util.errorDisplay("Segment closed surface is empty")
            return None, None
    
        return segmentId, polyData