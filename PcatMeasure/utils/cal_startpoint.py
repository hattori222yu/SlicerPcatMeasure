# -*- coding: utf-8 -*-
"""
Created on Sun Nov 30 10:41:04 2025

@author: Hattori
"""
import numpy as np
def cal_start_point(ct_coordinate,dicom_voxel_corrdinate):
    
    dicom_voxel_corrdinate = np.array(dicom_voxel_corrdinate)
    
    
    distances = np.linalg.norm(dicom_voxel_corrdinate - ct_coordinate, axis=1)
    closest_index = np.argmin(distances)

    
    return closest_index