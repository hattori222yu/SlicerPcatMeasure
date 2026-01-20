# -*- coding: utf-8 -*-
"""
Created on Sun Nov 30 10:41:04 2025

@author: Hattori
"""
import numpy as np
def cal_start_point(ct_coordinate,dicom_voxel_corrdinate):
    #########################################################################################################
    # 例：指定された点
    #ct_coordinate = np.array([181, 225, 248])

    # points_culmulative_voxel が numpy 配列であることを前提とします
    # もしまだなら np.array() で変換してください
    #########################################################################################################
    dicom_voxel_corrdinate = np.array(dicom_voxel_corrdinate)
    
    ########################################################################################################
    # ユークリッド距離の最小インデックスを取得
    #########################################################################################################
    distances = np.linalg.norm(dicom_voxel_corrdinate - ct_coordinate, axis=1)
    closest_index = np.argmin(distances)

    # 出力
    #rint(f"指定した座標: {ct_coordinate}")
    #rint(f"最も近い座標: {dicom_voxel_corrdinate[closest_index]}")
    #rint(f"最も近い点のインデックス: {closest_index}")
    return closest_index