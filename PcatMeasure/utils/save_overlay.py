# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 08:08:01 2025

@author: Hattori
"""
import numpy as np
#import matplotlib.pyplot as plt
import slicer.util
import vtk
import slicer
import numpy as np
import os


def exportSegToLabel(segNode, referenceVolumeNode):
    
    labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")

   
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
        segNode,
        ["seg_artery_PCAT"],  
        labelNode,
        referenceVolumeNode
    )
    return labelNode    

def saveOverlayImage(ctNode, labelNode, outputDir):
    os.makedirs(outputDir, exist_ok=True)

    # NumPy （z, y, x）
    ct_img = slicer.util.arrayFromVolume(ctNode)
    mask_img = slicer.util.arrayFromVolume(labelNode)

    spacing = ctNode.GetSpacing()
    origin = ctNode.GetOrigin()

    for z in range(ct_img.shape[0]):

        ct_slice = ct_img[z]
        mask_slice = mask_img[z]

        # -----------------------------
        # CT slice → vtkImageData
        # -----------------------------
        ct_vtk = vtk.vtkImageData()
        ct_vtk.SetDimensions(ct_slice.shape[1], ct_slice.shape[0], 1)
        ct_vtk.SetSpacing(spacing[0], spacing[1], 1)
        ct_vtk.SetOrigin(origin[0], origin[1], 0)
        ct_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

        # window/level（-200〜300）
        wl_min, wl_max = -200, 300
        ct_norm = np.clip(ct_slice, wl_min, wl_max)
        ct_norm = ((ct_norm - wl_min) / (wl_max - wl_min) * 255).astype(np.uint8)

        for y in range(ct_norm.shape[0]):
            for x in range(ct_norm.shape[1]):
                v = ct_norm[y, x]
                ct_vtk.SetScalarComponentFromFloat(x, y, 0, 0, v)
                ct_vtk.SetScalarComponentFromFloat(x, y, 0, 1, v)
                ct_vtk.SetScalarComponentFromFloat(x, y, 0, 2, v)

        # -----------------------------
        # Mask slice → vtkImageData
        # -----------------------------
        mask_vtk = vtk.vtkImageData()
        mask_vtk.SetDimensions(mask_slice.shape[1], mask_slice.shape[0], 1)
        mask_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

        for y in range(mask_slice.shape[0]):
            for x in range(mask_slice.shape[1]):
                if mask_slice[y, x] > 0:
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 0, 255)  # R
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 1, 0)    # G
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 2, 0)    # B
                else:
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 0, 0)
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 1, 0)
                    mask_vtk.SetScalarComponentFromFloat(x, y, 0, 2, 0)

        # -----------------------------
        # Blend
        # -----------------------------
        blend = vtk.vtkImageBlend()
        blend.AddInputData(ct_vtk)
        blend.AddInputData(mask_vtk)
        blend.SetOpacity(0, 1.0)
        blend.SetOpacity(1, 0.5)
        blend.Update()

        # -----------------------------
        # Save PNG
        # -----------------------------
        writer = vtk.vtkPNGWriter()
        writer.SetInputData(blend.GetOutput())
        savePath = os.path.join(outputDir, f"overlay_{z:04d}.png")
        writer.SetFileName(savePath)
        writer.Write()

    print(f"Saved overlay images to {outputDir}")