import slicer
import vtk
import numpy as np
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import qt
import logging
logging.getLogger().setLevel(logging.DEBUG)
class CoronaryCenterlineCrossSection(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Coronary Centerline Cross Section"
        parent.categories = ["Cardiology"]
        parent.dependencies = []
        parent.contributors = ["Hattori(yamagata)"]
        parent.helpText = (
            """
        This module displays vessel-orthogonal cross-sections along a coronary
        artery centerline and allows interactive placement of closed curves
        for precise lumen segmentation.

        Typical workflow:
        1. Load coronary CTA and centerline
        2. Scroll along centerline
        3. Place/edit lumen contours
        """
        )
        parent.acknowledgementText = "Uses VTK and 3D Slicer."


class CoronaryCenterlineCrossSectionWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        VTKObservationMixin.__init__(self)

        self.logic = CoronaryCenterlineCrossSectionLogic()
        self.resetWidgetState()
        # --- CTボリュームセレクタ ---
        self.ctSelector = slicer.qMRMLNodeComboBox()
        self.ctSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.ctSelector.selectNodeUponCreation = False
        self.ctSelector.addEnabled = False
        self.ctSelector.removeEnabled = False
        self.ctSelector.noneEnabled = True
        self.ctSelector.setMRMLScene(slicer.mrmlScene)
        self.ctSelector.setToolTip("Select CT volume")
        
        


        # --- Centerline selector ---
        self.centerlineSelector = slicer.qMRMLNodeComboBox()
        self.centerlineSelector.nodeTypes = ["vtkMRMLMarkupsCurveNode"]
        self.centerlineSelector.selectNodeUponCreation = False
        self.centerlineSelector.addEnabled = False
        self.centerlineSelector.removeEnabled = False
        self.centerlineSelector.noneEnabled = True
        self.centerlineSelector.setMRMLScene(slicer.mrmlScene)
        self.centerlineSelector.setToolTip("Select centerline (Markups Curve)")
        

        # --- Slider --- 直交断面のスライスインデックス
        self.slider = slicer.qMRMLSliderWidget()
        self.slider.minimum = 0
        self.slider.maximum = 0
        self.slider.decimals = 0
        self.slider.singleStep = 1
        self.slider.setToolTip("Centerline index")
        
        # --- step_mm slider スライス間の補間の間隔---
        self.stepMmSlider = slicer.qMRMLSliderWidget()
        self.stepMmSlider.minimum = 0.05
        self.stepMmSlider.maximum = 1.0
        self.stepMmSlider.value = 0.2
        self.stepMmSlider.decimals = 2
        self.stepMmSlider.singleStep = 0.05
        self.stepMmSlider.setToolTip("Slice step along centerline [mm]")
        
        # --- nResample spinbox 6点の円を何点に補間するか---
        self.nResampleSlider = slicer.qMRMLSliderWidget()
        self.nResampleSlider.minimum = 8
        self.nResampleSlider.maximum = 256
        self.nResampleSlider.value = 64
        self.nResampleSlider.singleStep = 8
        self.nResampleSlider.decimals = 0  
        self.nResampleSlider.setToolTip("Number of points on circle (integer)")
                
        # --- smoothing kernel slider ---　lumenセグメンテーションをどのくらいのsmoothingにする
        self.kernelSizeSlider = slicer.qMRMLSliderWidget()
        self.kernelSizeSlider.minimum = 0.0
        self.kernelSizeSlider.maximum = 2.0
        self.kernelSizeSlider.value = 0.2
        self.kernelSizeSlider.decimals = 2
        self.kernelSizeSlider.singleStep = 0.1
        self.kernelSizeSlider.setToolTip("Smoothing kernel size [mm]")
        
        
        # --- radius kernel --- 初期セグメンテーションからどのくらいの幅に広げてlumenとするかの係数
        self.radiusScaleSlider = slicer.qMRMLSliderWidget()
        self.radiusScaleSlider.minimum = 0.8    # 0.8
        self.radiusScaleSlider.maximum = 2.0   # 2.0
        self.radiusScaleSlider.value = 1.5     # 1.4
        self.radiusScaleSlider.singleStep = 0.05
        self.radiusScaleSlider.decimals = 2
                

        # --- Segment Vessel ボタン ---
        self.segmentButton = qt.QPushButton("Apply")
        
        self.segmentButton.connect("clicked(bool)", self.onSegmentButtonClicked)

        # --- Segment Vessel ボタン ---
        self.segmentButton2 = qt.QPushButton("Apply")
        
        self.segmentButton2.connect("clicked(bool)", self.onSegmentButtonClicked2)

        # --- Connections ---
        self.centerlineSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onCenterlineChanged)
        self.slider.connect("valueChanged(double)", self.onSliderChanged)
        self.ctSelector.connect("currentNodeChanged(vtkMRMLNode*)",self.onCTVolumeChanged)
        self.radiusScaleSlider.valueChanged.connect(self.onRadiusScaleChanged)        

        
        #---- layout
        layout = self.layout
        
        #CTセレクターのレイアウト
        formLayout = qt.QFormLayout()
        formLayout.setLabelAlignment(qt.Qt.AlignLeft)
        formLayout.setFormAlignment(qt.Qt.AlignLeft | qt.Qt.AlignTop)
        formLayout.setHorizontalSpacing(8)
        formLayout.setVerticalSpacing(6)
        
        # --- CT ---
        label = qt.QLabel("[1]: Select CT volume")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.ctSelector)
        
        # --- Centerline ---
        label = qt.QLabel("[2]: Select Centerline")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.centerlineSelector)
        

        formLayout.addRow("step along centerline (mm)", self.stepMmSlider)
        formLayout.addRow("circle resample points", self.nResampleSlider)
        formLayout.addRow("smoothing kernel size", self.kernelSizeSlider)
        formLayout.addRow("lumen kernel size", self.radiusScaleSlider)
        layout.addLayout(formLayout)
        
        label = qt.QLabel("[3]: Modified artery seg")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.segmentButton)
        
        label = qt.QLabel("center line index")
        formLayout.addRow(label, self.slider)
        
        
        
        label = qt.QLabel("[4]: Create artery seg")
        label.setStyleSheet("font-weight: bold;")
        formLayout.addRow(label, self.segmentButton2)
        
        self.pcatButton = qt.QPushButton("Go to PCAT Measurement")
        self.pcatButton.setToolTip("Open the PCAT Measurement module")
        layout.addWidget(self.pcatButton)
                
        self.pcatButton.connect("clicked(bool)", self.onPCATButtonClicked)

        layout.addStretch(1)
    def resetWidgetState(self):
        self.segNode = None
        self.segmentationReady = False
        self.prevIndex = None
        self.segNode_lumen=None
        
    def onCenterlineChanged(self, node):
        if not node:
            return
        self.logic.setCenterline(node)
        n = node.GetNumberOfControlPoints()
        self.slider.minimum = 0
        self.slider.maximum = max(n - 1, 0)
        #self.slider.value = 0
        #self.logic.updateSlice(0)
        if node is None:
            return None
        
        if node.GetNumberOfControlPoints() == 0:
            return None
    
        p = [0.0, 0.0, 0.0]
        node.GetNthControlPointPositionWorld(0, p)
         # --- ParameterNode に保存 ---
        paramNode = slicer.mrmlScene.GetFirstNodeByName("PCATParameters")
        if not paramNode:
            paramNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScriptedModuleNode", "PCATParameters"
            )
    
        paramNode.SetParameter(
            "CenterlineStartPointRAS",
            ",".join(map(str, p))
        )
        
    def enableWheelControl(self):
        # Red slice を基準にする（必要なら Yellow / Green に変更）
        sliceWidget = slicer.app.layoutManager().sliceWidget("Red")
        self.sliceView = sliceWidget.sliceView()
    
        self._wheelFilter = WheelToSliderFilter(self)
        self.sliceView.installEventFilter(self._wheelFilter)   
        
    def onSliderChanged(self, value):
        if not self.segmentationReady:
            return
        # 前の円を保存 ---
        if self.prevIndex is not None:
            self.logic.updateCircleFromMarkup(self.prevIndex)
        #self.logic.updateCircleFromMarkup(int(value))
        self.logic.updateSlice(int(value), self.segNode, "Vessel",self.radiusScaleSlider.value)
        self.prevIndex = int(value)
        
    def onRadiusScaleChanged(self, value):
        scale = value / 100.0
        #self.radiusScaleLabel.text = f"Radius scale: {scale:.2f}"    
            
    def onSegmentButtonClicked(self):
        ctNode = self.ctSelector.currentNode()
        centerlineNode = self.centerlineSelector.currentNode()
        if not ctNode or not centerlineNode:
            slicer.util.errorDisplay("CT volume or centerline not selected")
            return
        #self.segNode=None
        #print("ctNode",ctNode,"centerlineNode",centerlineNode)
        print("self.segNode",self.segNode,self.radiusScaleSlider.value)
        
        #（１）初期セグメンテーション。単純な閾値処理で冠動脈の内腔をセグメンテーション
        self.segNode = self.logic.segmentVesselAlongCenterline(ctNode, centerlineNode)
        
        # ラグON
        self.segmentationReady = True
        #slider を初期化
        self.slider.blockSignals(True)
        self.slider.value = 0
        self.slider.blockSignals(False)
        print("onSegmentButtonClicked!")
        # 最初のスライスを明示的に更新
        self.logic.updateSlice(0, self.segNode, "Vessel",self.radiusScaleSlider.value)
        slicer.util.infoDisplay(f"Segmented vessel created: {self.segNode.GetName()}")
        self.setupSegmentationDisplay(self.segNode)
        
        self.enableWheelControl()   
        
    def onSegmentButtonClicked2(self):
        self.disableWheelControl()
        #スライス補間間隔，円補間間隔，jointsmoothinのカーネルサイズの係数を取得
        step_mm = self.stepMmSlider.value
        nResample = int(self.nResampleSlider.value)
        kernelSizeMm = self.kernelSizeSlider.value
            
        #print(step_mm,nResample,kernelSizeMm)
        
        
        circles =self.logic.interpolateSliceCircles(step_mm=step_mm)
        self.logic.sliceCircles = circles
        polyData = self.logic.buildCylinderPolyData(nResample=nResample)
        
        #print("points:", polyData.GetNumberOfPoints())
        #print("polys :", polyData.GetNumberOfPolys())
        self.segNode_lumen = self.logic.createCylinderSegmentation(
            polyData,
            referenceVolumeNode=self.ctSelector.currentNode(),
            kernelSizeMm=kernelSizeMm
        )
        
        
        
    def setupSegmentationDisplay(self, segNode):
  
        displayNode = segNode.GetDisplayNode()

        # 色（黄色）
        segmentation = segNode.GetSegmentation()
        segmentId = segmentation.GetNthSegmentID(0)
        segmentation.GetSegment(segmentId).SetColor(1.0, 1.0, 0.0)
    
        # --- 表示設定 ---
        displayNode.SetVisibility(True)
        displayNode.SetVisibility2DFill(False)   # 塗りつぶしOFF
        # 塗りつぶし（Closed surface）をオフ
        displayNode.SetVisibility3D(False)
    
        # 輪郭（Outline）をオン
        displayNode.SetVisibility2DOutline(True)
    
        # 輪郭の太さ
        displayNode.SetSliceIntersectionThickness(1)
        
        
    def onCTVolumeChanged(self, volumeNode):
        if not volumeNode:
            return
    
        displayNode = volumeNode.GetDisplayNode()
        if not displayNode:
            volumeNode.CreateDefaultDisplayNodes()
            displayNode = volumeNode.GetDisplayNode()
    
        # --- Auto を OFF ---
        displayNode.AutoWindowLevelOff()
    
        # --- 冠動脈用 Window / Level ---
        displayNode.SetWindow(640)
        displayNode.SetLevel(150)
    
        # 任意：全スライスに反映
        displayNode.Modified()
        
    def hideMarkupIn3D(self,markupNode):
        if not markupNode:
            return
        displayNode = markupNode.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility3D(False)    
    def onPCATButtonClicked(self):
        import vtk
        import slicer
        # PCAT Measurement モジュールに切り替える
        self.disableWheelControl()
        slicer.util.selectModule("PcatMeasure")
    
        # Widget を取得
        pcatWidget = slicer.modules.pcatmeasure.widgetRepresentation().self()
        if pcatWidget is None:
            print("PCAT module widget not found")
            return
        pcatWidget.resetWidgetState()

        #print("caseNodeIDs",self.logic.caseNodeIDs)
        #Segmentation → Closed surface 取得
        segmentation = self.segNode_lumen.GetSegmentation()
        segmentId = segmentation.GetNthSegmentID(0)
        
        polyData = vtk.vtkPolyData()
        ok = slicer.modules.segmentations.logic().GetSegmentClosedSurfaceRepresentation(
            self.segNode_lumen,
            segmentId,
            polyData
        )
        
        #print("ok:", ok)
        #print("surface points:", polyData.GetNumberOfPoints())
        #node = slicer.mrmlScene.GetFirstNodeByName("VesselSeg")
        #slicer.mrmlScene.RemoveNode(node)
        
        #
        self.hideMarkupIn3D(self.centerlineSelector.currentNode())
        self.hideMarkupIn3D(self.logic.closedCurveNode)
            
        # CTと Segmentation を設定
        if hasattr(pcatWidget, 'ctSelector') and self.ctSelector.currentNode():
            pcatWidget.ctSelector.setCurrentNode(self.ctSelector.currentNode())
    
        if hasattr(pcatWidget, 'segmentSelector') and self.segNode_lumen:
            pcatWidget.segmentSelector.setCurrentNode(self.segNode_lumen)
        pcatWidget.setCaseNodeIDs(self.logic.caseNodeIDs,self.logic.caseNodeIDs_2)

            
    def disableWheelControl(self):
        if hasattr(self, "_wheelFilter") and self._wheelFilter:
            self.sliceView.removeEventFilter(self._wheelFilter)
            self._wheelFilter = None
            
#%%%%%%  ここからLogic class

class CoronaryCenterlineCrossSectionLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        self.initialize()
    def initialize(self):
        
        self.centerlineNode = None
        self.closedCurveNode = None
        self.sliceNode = slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceNode()
        self.longSliceNode = slicer.app.layoutManager().sliceWidget("Yellow").mrmlSliceNode()
        self.orthoSliceNode = slicer.app.layoutManager().sliceWidget("Green").mrmlSliceNode()

        self.sliceCircles = {} 
        self.caseNodeIDs = []
        self.caseNodeIDs_2 = []
    def reset(self):
        """再実行用の完全リセット"""
        self.initialize()
    def setCenterline(self, node):
        self.centerlineNode = node
        
    #%%　スライダーボタンの処理
    #最初のidx＝０で渡している
    def updateSlice(self, idx,segNode=None, segmentName=None,scaleFactor=1.5):
        
        if not self.centerlineNode:
            return

        n = self.centerlineNode.GetNumberOfControlPoints()
        if n < 2:
            return
        #接線を計算するためidxの前後のインデックス値を取得。端点の場合はclamp処理
        idx0 = max(idx - 1, 0)
        idx1 = min(idx + 1, n - 1)
        #インデックス値から前後の中心線座標の取得。pが今のスライスのインデックス値。p0は1つ前、p1は１つ後。
        p0 = np.array(self.centerlineNode.GetNthControlPointPositionWorld(idx0))
        p1 = np.array(self.centerlineNode.GetNthControlPointPositionWorld(idx1))
        p  = np.array(self.centerlineNode.GetNthControlPointPositionWorld(idx))
        #接線ベクトル（tangent）の計算
        tangent = p1 - p0
        norm = np.linalg.norm(tangent)
        if norm < 1e-6:
            return
        tangent /= norm
        #各スライスビューの更新
        #red
        self._updateSliceNode(p, tangent)
        #yello
        self._updateLongitudinalSliceNode(p, tangent)
        #green
        self._updateOrthogonalSliceNode(p, tangent)
        
        
        #Closed circle（血管断面円）
        
        #scale = self.radiusScaleSlider.value 
        #すでに手動編集されてたらこっち
        if idx in self.sliceCircles and self.sliceCircles[idx].get("edited", False):
            #print("へんしゅうされているidx",idx)
            self._restoreClosedCircleFromCache(idx)
        #編集されてないならこっち
        else:
            #print("編集されていないidx",idx)
            self._updateClosedCircleFromSegmentation(segNode, segmentName, idx,scaleFactor=scaleFactor)
    def _ensureClosedCurveNode(self):
        import slicer
    
        if (not self.closedCurveNode or
            not slicer.mrmlScene.IsNodePresent(self.closedCurveNode)):
    
            self.closedCurveNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsClosedCurveNode",
                "  "
            )
            self.closedCurveNode.CreateDefaultDisplayNodes()
    
        displayNode = self.closedCurveNode.GetDisplayNode()
        if not displayNode:
            self.closedCurveNode.CreateDefaultDisplayNodes()
            displayNode = self.closedCurveNode.GetDisplayNode()
    
        displayNode.SetGlyphScale(3)
        displayNode.SetVisibility(True)        
    #手動編集されている場合の処理
    def _restoreClosedCircleFromCache(self, idx, n=6):
        data = self.sliceCircles[idx]
        self._ensureClosedCurveNode()
        """
        if not self.closedCurveNode:
            self.closedCurveNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsClosedCurveNode"
            )
            self.closedCurveNode.CreateDefaultDisplayNodes()
            self.closedCurveNode.GetDisplayNode().SetGlyphScale(3)
        """
    
        self.closedCurveNode.RemoveAllControlPoints()
    
        for p in data["controlPoints"]:
            self.closedCurveNode.AddControlPointWorld(p)    
    
    #手動編集されてない場合の処理
    def _updateClosedCircleFromSegmentation(self, segNode, segmentName,idx ,n=6,scaleFactor=1.5):
        import numpy as np
        import slicer
        #セグメントID取得
        segmentId = segNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)
        if not segmentId:
            return
        #スライス断面での輪郭抽出。この時点では、まだ初期内腔セグメンテーションの任意断面の輪郭のみを計算し返しているだけ。
        #このcontourは１断面に複数セグメンテーションが存在するときすべてのセグメンテーションの断面の情報を持っている
        contour = self._extractSegmentationContourOnSlice(segNode, segmentId)
        if contour is None:
            return
        #contourのデータから今の中心線点（＝インデックス値）に一番近い中心線の座標を取得
        centerlinePoint = np.array(self.centerlineNode.GetNthControlPointPositionWorld(idx))
        
        contour = self._selectClosestContour(contour, centerlinePoint)
        if contour is None:
            return
        #円フィッティング断面輪郭を slice 座標系 (x,y) に落とす.円近似（重心＋平均半径）
        center, radius = self._fitCircleOnSlice(contour)
        if center is None:
            return
        # --- ClosedCurve node ---
        """
        if not self.closedCurveNode or not self.closedCurveNode.GetScene():
            self.closedCurveNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsClosedCurveNode",
                " "
            )
            self.closedCurveNode.CreateDefaultDisplayNodes()
            self.closedCurveNode.GetDisplayNode().SetGlyphScale(3)
            self.caseNodeIDs.append(self.closedCurveNode.GetID())
            self.caseNodeIDs_2.append(self.centerlineNode.GetID())
            
        """
        
        self._ensureClosedCurveNode()
        self.caseNodeIDs.append(self.closedCurveNode.GetID())
        self.caseNodeIDs_2.append(self.centerlineNode.GetID())
        self.closedCurveNode.RemoveAllControlPoints()
        #スライス平面の基底取得
        mat = self.sliceNode.GetSliceToRAS()
        xAxis = np.array([mat.GetElement(i, 0) for i in range(3)])
        yAxis = np.array([mat.GetElement(i, 1) for i in range(3)])
        #1.4は適当な値輪郭より少し大きくする．
        radius=radius*scaleFactor
        
        pts = []  # controlPoints 用
        #円周点生成
        for i in range(n):
            theta = 2 * np.pi * i / n
            p = center + radius * (
                np.cos(theta) * xAxis + np.sin(theta) * yAxis
            )
            self.closedCurveNode.AddControlPointWorld(p.tolist())
            p_list = p.tolist() 
            pts.append(p_list)  #  ここで保存
        self.sliceCircles[idx] = {"center": center.copy(),
            "radius": radius,
            "xAxis": xAxis.copy(),
            "yAxis": yAxis.copy(),
            "edited":False,
            "controlPoints": pts }    
    
    def _extractSegmentationContourOnSlice(self, segNode, segmentId):
        import vtk
        import slicer
        import numpy as np
    
        # --- segmentation → surface polydata ---
        segmentation = segNode.GetSegmentation()
        polyData = vtk.vtkPolyData()
        slicer.modules.segmentations.logic().GetSegmentClosedSurfaceRepresentation(
            segNode, segmentId, polyData
        )
    
        if polyData.GetNumberOfPoints() == 0:
            return None
    
        # --- slice plane ---
        sliceToRAS = self.sliceNode.GetSliceToRAS()
        #Slice 平面定義
        origin = np.array([sliceToRAS.GetElement(i, 3) for i in range(3)])
        normal = np.array([sliceToRAS.GetElement(i, 2) for i in range(3)])
        normal /= np.linalg.norm(normal)
    
        plane = vtk.vtkPlane()
        plane.SetOrigin(origin.tolist())
        plane.SetNormal(normal.tolist())
    
        # --- cutter ---vtkCutter で切断
        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputData(polyData)
        cutter.Update()
    
        contour = cutter.GetOutput()
        if contour.GetNumberOfPoints() < 10:
            return None
    
        return contour
    def _selectClosestContour(self, contourPolyData, centerlinePointRAS):
        import vtk
        import numpy as np
    
        connectivity = vtk.vtkPolyDataConnectivityFilter()
        connectivity.SetInputData(contourPolyData)
        connectivity.SetExtractionModeToAllRegions()
        connectivity.ColorRegionsOn()
        connectivity.Update()
    
        labeled = connectivity.GetOutput()
        regionIds = labeled.GetPointData().GetArray("RegionId")
        nRegions = connectivity.GetNumberOfExtractedRegions()
    
        bestPoly = None
        bestDist = np.inf
    
        for rid in range(nRegions):
            thresh = vtk.vtkThreshold()
            thresh.SetInputData(labeled)
            thresh.SetInputArrayToProcess(
                0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "RegionId"
            )
            thresh.ThresholdBetween(rid, rid)
            thresh.Update()
    
            geom = vtk.vtkGeometryFilter()
            geom.SetInputData(thresh.GetOutput())
            geom.Update()
    
            poly = geom.GetOutput()
            if poly.GetNumberOfPoints() < 10:
                continue
    
            pts = np.array([poly.GetPoint(i) for i in range(poly.GetNumberOfPoints())])
            centroid = pts.mean(axis=0)
    
            d = np.linalg.norm(centroid - centerlinePointRAS)
            if d < bestDist:
                bestDist = d
                bestPoly = poly
    
        return bestPoly
    def _fitCircleOnSlice(self, contourPolyData):
        import numpy as np
    
        # slice 座標系
        mat = self.sliceNode.GetSliceToRAS()
    
        xAxis = np.array([mat.GetElement(i, 0) for i in range(3)])
        yAxis = np.array([mat.GetElement(i, 1) for i in range(3)])
        origin = np.array([mat.GetElement(i, 3) for i in range(3)])
    
        pts2d = []
    
        for i in range(contourPolyData.GetNumberOfPoints()):
            p = np.array(contourPolyData.GetPoint(i))
            v = p - origin
            x = np.dot(v, xAxis)
            y = np.dot(v, yAxis)
            pts2d.append([x, y])
    
        pts2d = np.array(pts2d)
    
        if pts2d.shape[0] < 10:
            return None, None
    
        cx = pts2d[:, 0].mean()
        cy = pts2d[:, 1].mean()
        r = np.mean(np.sqrt((pts2d[:, 0] - cx)**2 + (pts2d[:, 1] - cy)**2))
    
        centerRAS = origin + cx * xAxis + cy * yAxis
        return centerRAS, r
    
    #axialのsliceviewをreformatにする
    def _updateSliceNode(self, origin, tangent):
        up = np.array([0, 0, 1])
        if abs(np.dot(up, tangent)) > 0.9:
            up = np.array([0, 1, 0])
    
        x = np.cross(up, tangent)
        x /= np.linalg.norm(x)
        y = np.cross(tangent, x)
    
        mat = vtk.vtkMatrix4x4()
        mat.Identity()
    
        for i in range(3):
            mat.SetElement(i, 0, x[i])
            mat.SetElement(i, 1, y[i])
            mat.SetElement(i, 2, tangent[i])
            mat.SetElement(i, 3, origin[i])
    
        sliceToRAS = self.sliceNode.GetSliceToRAS()
        sliceToRAS.DeepCopy(mat)
        self.sliceNode.UpdateMatrices()
    #縦断面のCTnode
    def _updateLongitudinalSliceNode(self, origin, tangent):
        import vtk
        import numpy as np
    
        up = np.array([0, 0, 1])
        if abs(np.dot(up, tangent)) > 0.9:
            up = np.array([0, 1, 0])
    
        # cross-section で使っている x, y
        x = np.cross(up, tangent)
        x /= np.linalg.norm(x)
        y = np.cross(tangent, x)
    
        #  縦断面
        # normal = x
        # plane contains tangent
        mat = vtk.vtkMatrix4x4()
        mat.Identity()
    
        for i in range(3):
            mat.SetElement(i, 0, tangent[i])  # 横方向：中心線方向
            mat.SetElement(i, 1, y[i])        # 縦方向
            mat.SetElement(i, 2, x[i])        # 法線
            mat.SetElement(i, 3, origin[i])
    
        sliceToRAS = self.longSliceNode.GetSliceToRAS()
        sliceToRAS.DeepCopy(mat)
        self.longSliceNode.UpdateMatrices()
    
    def _updateOrthogonalSliceNode(self, origin, tangent):
        import vtk
        import numpy as np
    
        up = np.array([0, 0, 1])
        if abs(np.dot(up, tangent)) > 0.9:
            up = np.array([0, 1, 0])
    
        x = np.cross(up, tangent)
        x /= np.linalg.norm(x)
        y = np.cross(tangent, x)
    
        # Green slice
        # normal = y
        mat = vtk.vtkMatrix4x4()
        mat.Identity()
    
        for i in range(3):
            mat.SetElement(i, 0, tangent[i])  # 横：中心線方向
            mat.SetElement(i, 1, x[i])        # 縦：円断面の横
            mat.SetElement(i, 2, y[i])        # 法線
            mat.SetElement(i, 3, origin[i])
    
        sliceToRAS = self.orthoSliceNode.GetSliceToRAS()
        sliceToRAS.DeepCopy(mat)
        self.orthoSliceNode.UpdateMatrices()
        
    
    #%% 最初のセグメンテーションボタンを押したら。まずここは中心線からある範囲の閾値処理を行って初期冠動脈の内腔のセグメンテーションを行う
    def segmentVesselAlongCenterline(self,ctVolumeNode,centerlineNode,threshold=(200, 500),radius_mm=2.5,outputSegName="VesselSeg" ):
        import vtk
        import slicer
        import numpy as np
    
        # --- CT情報 ---
        spacing = ctVolumeNode.GetSpacing()
        dims = ctVolumeNode.GetImageData().GetDimensions()
    
        ct_array = slicer.util.arrayFromVolume(ctVolumeNode)
    
        # --- 内部用 LabelMap 作成 ---
        labelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode",
            "__tmp_vessel_label__"
        )
        labelNode.CopyOrientation(ctVolumeNode)
        labelNode.SetAndObserveImageData(vtk.vtkImageData())
        labelNode.GetImageData().SetDimensions(dims)
        labelNode.GetImageData().AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
        labelNode.GetImageData().GetPointData().GetScalars().Fill(0)
        labelNode.CreateDefaultDisplayNodes()
        labelNode.GetDisplayNode().SetVisibility(False)
        label_array = slicer.util.arrayFromVolume(labelNode)
    
        # RAS → IJK 行列
        rasToIjk = vtk.vtkMatrix4x4()
        ctVolumeNode.GetRASToIJKMatrix(rasToIjk)
    
        # 中心線に沿って処理
        n_points = centerlineNode.GetNumberOfControlPoints()
    
        for i in range(n_points):
            p = centerlineNode.GetNthControlPointPositionWorld(i)
    
            ijk4 = [0.0, 0.0, 0.0, 0.0]
            rasToIjk.MultiplyPoint(list(p) + [1.0], ijk4)
            ijk = np.round(ijk4[:3]).astype(int)
    
            if np.any(ijk < 0) or np.any(ijk >= np.array(dims)):
                continue
    
            radius_vox = np.array(radius_mm / np.array(spacing))
    
            for x in range(
                max(0, ijk[0]-int(radius_vox[0])),
                min(dims[0], ijk[0]+int(radius_vox[0])+1)
            ):
                for y in range(
                    max(0, ijk[1]-int(radius_vox[1])),
                    min(dims[1], ijk[1]+int(radius_vox[1])+1)
                ):
                    for z in range(
                        max(0, ijk[2]-int(radius_vox[2])),
                        min(dims[2], ijk[2]+int(radius_vox[2])+1)
                    ):
                        d2 = (
                            ((x-ijk[0])*spacing[0])**2 +
                            ((y-ijk[1])*spacing[1])**2 +
                            ((z-ijk[2])*spacing[2])**2
                        )
                        if d2 <= radius_mm**2:
                            if threshold[0] <= ct_array[z, y, x] <= threshold[1]:
                                label_array[z, y, x] = 1
    
        slicer.util.updateVolumeFromArray(labelNode, label_array)
    
        #SegmentationNode 作成 
        segNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode",
            outputSegName
        )
        segNode.CreateDefaultDisplayNodes()
        segNode.SetReferenceImageGeometryParameterFromVolumeNode(ctVolumeNode)
    
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            segNode
        )
    
        # Segment名設定
        segmentation = segNode.GetSegmentation()
        segmentId = segmentation.GetNthSegmentID(0)
        segmentation.GetSegment(segmentId).SetName("Vessel")
        segNode.CreateDefaultDisplayNodes()
        segNode.GetDisplayNode().SetVisibility(False)
        # 一時ラベル削除
        #slicer.mrmlScene.RemoveNode(labelNode)
        #後で消すように
        self.caseNodeIDs.append(labelNode.GetID())
        self.caseNodeIDs.append(segNode.GetID())

        return segNode
    
    
    
    
    #%% onsegmentation button２を押したら    
    def hexagonToDistortedCircle(self,controlPoints,center,xAxis,yAxis,nSamples=64,smooth=True):
        import numpy as np
    
        xAxis = xAxis / np.linalg.norm(xAxis)
        yAxis = yAxis / np.linalg.norm(yAxis)
    
        pts = np.asarray(controlPoints)
    
        rel = pts - center
        xs = rel @ xAxis
        ys = rel @ yAxis
    
        angles = np.arctan2(ys, xs)
        radii  = np.sqrt(xs**2 + ys**2)
    
        order = np.argsort(angles)
        angles = angles[order]
        radii  = radii[order]
    
        angles = np.concatenate([angles, angles[:1] + 2*np.pi])
        radii  = np.concatenate([radii, radii[:1]])
    
        theta_new = np.linspace(0, 2*np.pi, nSamples, endpoint=False)
        radii_new = np.interp(theta_new, angles, radii)
    
        if smooth:
            print("SMOOTHING!!!")
            kernel = np.array([1, 2, 3, 2, 1], float)
            kernel /= kernel.sum()
            radii_new = np.convolve(
                np.r_[radii_new[-2:], radii_new, radii_new[:2]],
                kernel,
                mode="same"
            )[2:-2]
    
        newPts = []
        for th, r in zip(theta_new, radii_new):
            p = center + r * (np.cos(th) * xAxis + np.sin(th) * yAxis)
            newPts.append(p)
    
        return np.array(newPts)
    #closed circleで作成したスライス間を補間するおおもとのやつ
    def interpolateSliceCircles(self, step_mm=0.2):
        import numpy as np
    
        keys = sorted(self.sliceCircles.keys())
        newCircles = {}
    
        for i in range(len(keys) - 1):
            k0, k1 = keys[i], keys[i + 1]
            c0 = self.sliceCircles[k0]
            c1 = self.sliceCircles[k1]
    
            
            if "controlPoints" not in c0 or "controlPoints" not in c1:
                continue
    
            pts0 = np.array(c0["controlPoints"])  # (N,3)
            pts1 = np.array(c1["controlPoints"])
    
            # 中心間距離で補間数決定
            p0 = c0["center"]
            p1 = c1["center"]
            dist = np.linalg.norm(p1 - p0)
            n = max(1, int(dist / step_mm))
    
            for j in range(n):
                t = j / n
                idx = k0 + t
    
                # 点ごとに補間してく（形状保存）
                pts_interp = (1 - t) * pts0 + t * pts1
    
                # center は controlPoints から再計算
                center = pts_interp.mean(axis=0)
    
                # xAxis, yAxis は元の線形補間でOK
                xAxis = (1 - t) * c0["xAxis"] + t * c1["xAxis"]
                yAxis = (1 - t) * c0["yAxis"] + t * c1["yAxis"]
    
                newCircles[idx] = {
                    "center": center,
                    "xAxis": xAxis,
                    "yAxis": yAxis,
                    "controlPoints": pts_interp.tolist(),
                    "edited": True
                }
    
        newCircles[keys[-1]] = self.sliceCircles[keys[-1]]
        return newCircles
    def _addCap(self, polys, ids, reverse=False):
        import vtk
        poly = vtk.vtkPolygon()
        n = len(ids)
        poly.GetPointIds().SetNumberOfIds(n)
        for i in range(n):
            poly.GetPointIds().SetId(
                i, ids[n - 1 - i] if reverse else ids[i]
            )
        polys.InsertNextCell(poly)
    #スライスポリゴンの点を補間する    
    def _resampleClosedPolygon(self,points, nSamples):
        import numpy as np
    
        pts = np.asarray(points)
        if not np.allclose(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[0]])
    
        # 辺長
        seglens = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        cumlen = np.insert(np.cumsum(seglens), 0, 0.0)
        total = cumlen[-1]
    
        # 等間隔距離
        target = np.linspace(0, total, nSamples + 1)[:-1]
    
        newPts = []
        for t in target:
            i = np.searchsorted(cumlen, t) - 1
            i = max(0, min(i, len(seglens) - 1))
            w = (t - cumlen[i]) / seglens[i] if seglens[i] > 0 else 0
            p = (1 - w) * pts[i] + w * pts[i + 1]
            newPts.append(p)
    
        return np.array(newPts)    
        
    
    def buildCylinderPolyData(self, nResample=32):
        import vtk
        import numpy as np
        #nResample=256
        #print(nResample)

        points = vtk.vtkPoints()
        polys  = vtk.vtkCellArray()
    
        sliceIds = []
        keys = sorted(self.sliceCircles.keys())
    
        for idx in keys:
            circle = self.sliceCircles[idx]
    
            pts = np.array(circle["controlPoints"])
    
            #  ここで「六角形 → 歪み円」に変換
            if len(pts) == 6:
                pts = self.hexagonToDistortedCircle(
                    pts,
                    circle["center"],
                    circle["xAxis"],
                    circle["yAxis"],
                    nSamples=nResample,
                    smooth=False
                )
    
            # ★ それ以外は通常 resample
            elif len(pts) != nResample:
                pts = self._resampleClosedPolygon(pts, nResample)
    
            ids = []
            for p in pts:
                ids.append(points.InsertNextPoint(p.tolist()))
            sliceIds.append(ids)
    
        # --- side walls ---
        for i in range(len(sliceIds) - 1):
            c0 = sliceIds[i]
            c1 = sliceIds[i + 1]
            n = len(c0)
    
            for j in range(n):
                quad = vtk.vtkQuad()
                quad.GetPointIds().SetId(0, c0[j])
                quad.GetPointIds().SetId(1, c0[(j + 1) % n])
                quad.GetPointIds().SetId(2, c1[(j + 1) % n])
                quad.GetPointIds().SetId(3, c1[j])
                polys.InsertNextCell(quad)
    
        # --- caps ---
        self._addCap(polys, sliceIds[0], reverse=True)
        self._addCap(polys, sliceIds[-1], reverse=False)
    
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetPolys(polys)
    
        return polyData
    
    def polyDataToModelNode(self, polyData, name="artery"):
        import slicer
        import vtk
    
        modelNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLModelNode",
            name
        )
        modelNode.SetAndObservePolyData(polyData)
    
        modelNode.CreateDefaultDisplayNodes()
        modelNode.GetDisplayNode().SetColor(1, 0, 0)
        modelNode.GetDisplayNode().SetOpacity(0.6)
        #後で消すように
        self.caseNodeIDs.append(modelNode.GetID())
        return modelNode
    
    #createCylinderSegmentationで作成したsegmentationをsmoothing
    def _smoothSegmentationJointInternal(
        self,
        segNode,
        referenceVolumeNode,
        kernelSizeMm=0.5,
    ):
        import slicer
    
        segmentation = segNode.GetSegmentation()
        segmentId = segmentation.GetNthSegmentID(0)
        if not segmentId:
            print("No segment found")
            return
    
        # --- Segment Editor Node ---
        editorNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentEditorNode"
        )
        editorNode.SetAndObserveSegmentationNode(segNode)
        editorNode.SetSelectedSegmentID(segmentId)
    
        # --- Segment Editor Widget（） ---
        editorWidget = slicer.qMRMLSegmentEditorWidget()
        editorWidget.setMRMLScene(slicer.mrmlScene)
        editorWidget.setMRMLSegmentEditorNode(editorNode)
        editorWidget.setSegmentationNode(segNode)
    
        #  Reference volume は widget に設定する
        editorWidget.setMasterVolumeNode(referenceVolumeNode)
    
        # --- Smoothing effect ---
        editorWidget.setActiveEffectByName("Smoothing")
        effect = editorWidget.activeEffect()
    
        effect.setParameter("SmoothingMethod",  "MORPHOLOGICAL")
        effect.setParameter("KernelSizeMm", kernelSizeMm)
    
        # --- Apply ---
        effect.self().onApply()
    
        # --- cleanup ---
        editorWidget = None
        slicer.mrmlScene.RemoveNode(editorNode)
                    
        
    #buildCylinderPolyDataで作成したpolydataをセグメンテーションか
    def createCylinderSegmentation(self, polyData, referenceVolumeNode, name="Artery",kernelSizeMm=0.5):
        import slicer
    
        # --- PolyData → Model ---
        modelNode = self.polyDataToModelNode(polyData)
    
        # --- Segmentation ---
        segNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode",
            name
        )
        segNode.CreateDefaultDisplayNodes()
        segNode.SetReferenceImageGeometryParameterFromVolumeNode(referenceVolumeNode)
    
        
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(
            modelNode,
            segNode
        )
        # Model を非表示
        modelNode.CreateDefaultDisplayNodes()
        modelNode.GetDisplayNode().SetVisibility(False)
        self.caseNodeIDs_2.append(segNode.GetID())
        # 一時作成したモデルを削除
        #slicer.mrmlScene.RemoveNode(modelNode)
        #今_smoothSegmentationJointInternalしていない。
        print("kernelSizeMm",kernelSizeMm)
        self._smoothSegmentationJointInternal(segNode,referenceVolumeNode,kernelSizeMm=kernelSizeMm )
        return segNode
    
    #%%% 手動で編集したら点の座標をupdateする
    def updateCircleFromMarkup(self, idx):
        import numpy as np
    
        if not self.closedCurveNode:
            return
    
        ptsRAS = self._getClosedCurvePointsRAS()
        if ptsRAS is None:
            return
    
        pts2d, origin, xAxis, yAxis = self._projectPointsToSlice2D(ptsRAS)
    
        cx, cy, r = self._fitCircle2D(pts2d)
    
        centerRAS = origin + cx * xAxis + cy * yAxis
        if not self.closedCurveNode:
            return
    
        pts = []
        for i in range(self.closedCurveNode.GetNumberOfControlPoints()):
            pts.append(
                self.closedCurveNode.GetNthControlPointPositionWorld(i)
            )
    
    
        self.sliceCircles[idx] = {
            "center": centerRAS.copy(),
            "radius": float(r),
            "xAxis": xAxis.copy(),
            "yAxis": yAxis.copy(),
            "edited": True,
            "controlPoints": pts
        }
    def _fitCircle2D(self, pts2d):
        import numpy as np
    
        x = pts2d[:, 0]
        y = pts2d[:, 1]
    
        A = np.column_stack([2*x, 2*y, np.ones(len(x))])
        b = x**2 + y**2
    
        c, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        cx, cy = c[0], c[1]
        r = np.mean(np.sqrt((x - cx)**2 + (y - cy)**2))
    
        return cx, cy, r
    def _projectPointsToSlice2D(self, ptsRAS):
        import numpy as np
    
        mat = self.sliceNode.GetSliceToRAS()
        origin = np.array([mat.GetElement(i, 3) for i in range(3)])
        xAxis  = np.array([mat.GetElement(i, 0) for i in range(3)])
        yAxis  = np.array([mat.GetElement(i, 1) for i in range(3)])
    
        pts2d = []
        for p in ptsRAS:
            v = p - origin
            x = np.dot(v, xAxis)
            y = np.dot(v, yAxis)
            pts2d.append([x, y])
    
        return np.array(pts2d), origin, xAxis, yAxis
    def _getClosedCurvePointsRAS(self):
        import numpy as np
    
        n = self.closedCurveNode.GetNumberOfControlPoints()
        if n < 3:
            return None
    
        pts = []
        for i in range(n):
            p = [0, 0, 0]
            self.closedCurveNode.GetNthControlPointPositionWorld(i, p)
            pts.append(p)
    
        return np.array(pts)
#%%%
class WheelToSliderFilter(qt.QObject):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def eventFilter(self, obj, event):
        if event.type() == qt.QEvent.Wheel:
            if event.modifiers() & qt.Qt.ControlModifier:
                return False   # 
            if not self.widget.segmentationReady:
                return True

            delta = event.angleDelta().y()
            if delta == 0:
                return True

            step = 1 if delta > 0 else -1

            slider = self.widget.slider
            newValue = int(slider.value + step)

            newValue = max(slider.minimum, min(slider.maximum, newValue))

            if newValue != slider.value:
                slider.value = newValue   #

            return True  # slice の通常スクロールをさせない

        return False