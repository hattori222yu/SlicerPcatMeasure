# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 11:27:14 2025

@author: Hattori
"""
import slicer.util
import slicer
import csv
import numpy as np
import os
def appendMeanToCSV(csvPath, filename, arteryname, meanValue,i,j,k):
    # フォルダがなければ作成
    os.makedirs(os.path.dirname(csvPath), exist_ok=True)

    fileExists = os.path.exists(csvPath)

    with open(csvPath, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # ヘッダ（初回のみ）
        if not fileExists:
            writer.writerow(["filename", "artery", "mean_CT_value","I","J","K"])

        writer.writerow([filename, arteryname, f"{meanValue:.3f}",i,j,k])

def getCTvaluesFromSegmentation(segNode, volumeNode,filename,arteryname,save_dir,branch_start_corrdinate):
    # --- 1. LabelMap へ変換 ---
    #referenceGeometry = slicer.modules.segmentations.logic().GetVolumeNodeGeometry(self.ctNode)

    labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
        segNode, labelNode,  slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY
    )

    # --- 2. LabelMap → NumPy array ---
    labelArray = slicer.util.arrayFromVolume(labelNode)
    #print("labelArray.shape",labelArray.shape)
    # --- 3. CT Volume → NumPy array ---
    ctArray = slicer.util.arrayFromVolume(volumeNode)
    #print("ctArray.shape",ctArray.shape)
    # --- 4. セグメントが存在する部分（label==1）を抽出 ---
    mask = labelArray > 0
    ct_values = ctArray[mask]

    # --- 5. labelNode を削除 ---
    slicer.mrmlScene.RemoveNode(labelNode)
    
    
    hu_min = -190
    hu_max = -30
    
    # ct_values はセグメント内ボクセルの HU 値が入った 1D numpy 配列
    masked_values = ct_values[(ct_values >= hu_min) & (ct_values <= hu_max)]
    
    if masked_values.size == 0:
        mean_hu = None   # 該当値がない場合
    else:
        mean_hu = masked_values.mean()
    
    if mean_hu.size == 0:
        slicer.util.warningDisplay("Segmentation is empty.")
    else:
        
        
    
        csvPath = os.path.join(
            save_dir,
            "PCAT_mean_CT.csv"
        )
    
        appendMeanToCSV(
            csvPath,
            filename,
            arteryname,
            mean_hu,
            branch_start_corrdinate[0],
            branch_start_corrdinate[1],
            branch_start_corrdinate[2],
        )
    
        
    
    
    
    
    return ct_values,masked_values,mean_hu