# -*- coding: utf-8 -*-
"""
Created on Wed Dec 24 06:51:12 2025

@author: Hattori
"""

import nibabel as nib
import numpy as np



img = nib.load("E:/coronary_data_600/1-200/2.img.nii.gz")
label = nib.load("E:/coronary_data_600/1-200/2.label.nii.gz")

label_data = label.get_fdata()

# img の affine をそのまま使う
new_affine = img.affine

new_label = nib.Nifti1Image(
    label_data.astype(np.uint8),
    new_affine,
    header=img.header  # ← これ重要
)

# intent を label 用に
new_label.set_data_dtype(np.uint8)

nib.save(new_label, "E:/coronary_data_600/1-200/2.label_fixed.nii.gz")