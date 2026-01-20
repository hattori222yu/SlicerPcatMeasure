# -*- coding: utf-8 -*-
"""
Created on Fri Dec 26 07:32:30 2025

@author: Hattori
"""
import slicer
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
