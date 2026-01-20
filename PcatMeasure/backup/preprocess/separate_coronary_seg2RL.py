import os
import glob
import shutil
import numpy as np
import nibabel as nib
from scipy.ndimage import label as cc_label
from scipy.ndimage import center_of_mass

input_dir = r"E:\coronary_data_600\201-400"
output_dir = r"E:\coronary_data_600_RL"
os.makedirs(output_dir, exist_ok=True)

label_files = glob.glob(os.path.join(input_dir, "*.label.nii.gz"))

def extract_number(path):
    return int(os.path.basename(path).split(".")[0])

label_files = sorted(label_files, key=extract_number)

for label_path in label_files:
    base = os.path.basename(label_path).replace(".label.nii.gz", "")

    nii = nib.load(label_path)
    data = nii.get_fdata()

    bin_data = (data > 0).astype(np.uint8)

    labeled, num = cc_label(bin_data)

    if num < 2:
        print(f"[WARNING] {base}: connected components = {num} (skip)")
        continue

    # X軸中央
    x_mid = bin_data.shape[2] / 2

    rca = np.zeros_like(bin_data)
    lca = np.zeros_like(bin_data)

    for i in range(1, num + 1):
        com = center_of_mass(bin_data, labeled, i)
        x = com[2]

        if x < x_mid:
            rca[labeled == i] = 1
        else:
            lca[labeled == i] = 1

    if rca.sum() == 0 or lca.sum() == 0:
        print(f"[WARNING] {base}: RCA or LCA empty (skip)")
        continue

    # --- label 保存 ---
    rca_nii = nib.Nifti1Image(rca, nii.affine, nii.header)
    lca_nii = nib.Nifti1Image(lca, nii.affine, nii.header)

    nib.save(rca_nii, os.path.join(output_dir, f"{base}.label_R.nii.gz"))
    nib.save(lca_nii, os.path.join(output_dir, f"{base}.label_L.nii.gz"))

    # --- img をコピー ---
    img_path = os.path.join(input_dir, f"{base}.img.nii.gz")
    if os.path.exists(img_path):
        shutil.copy2(img_path, os.path.join(output_dir, f"{base}.img.nii.gz"))
    else:
        print(f"[WARNING] {base}: img file not found")

    print(f"[OK] {base}: RCA / LCA saved & img copied")
