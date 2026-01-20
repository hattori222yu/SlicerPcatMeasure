import pickle
import numpy as np

pickle_path = r"C:\Users\fight\Pcat_measure\output\1_img_nii_gz\error_seg_from_cross\00_centerCurve_coord_voxel_RCA.pickle"

with open(pickle_path, "rb") as f:
    data = pickle.load(f)

        
for k, pts in data.items():
    print(f"\nBranch {k}")
    print("  shape:", pts.shape)
    print("  first 5 points:")
    print(pts[:5])
    
    
    
    ###############################################################
    
import slicer
import numpy as np
import vtk

# ---- voxel (IJK) 座標 ----
"""
points_ijk = np.array([
    [196.93406685, 364.58929728, 124.38802338],
    [197.30769562, 365.85152202, 126.12210846],
    [197.00301824, 367.99955473, 127.25272369],
    [197.70100996, 369.90284974, 128.57523346],
    [197.99438097, 371.91495304, 129.79451752],
])
"""
points_ijk = np.array([
[126.18932157, 395.35229113, 89.23720551],
[128.31404074, 394.75376457, 90.32195282],
[130.56742329, 394.10678433, 91.22614288],
[132.46121832, 393.92138925, 92.61994171],
[134.25373168, 394.13447215, 94.07009125],
])
points_ijk = np.array([
[157.39933026, 393.52833549, 130.24398041],
[158.30590852, 392.6050842, 132.02933502],
[160.28796561, 391.7222717, 133.29485321],
[162.55328509, 391.00943167, 134.33777618],
[164.92295497, 390.34901231, 135.26084137],
])

# ---- 正しい CT volume node を取得 ----
lm = slicer.app.layoutManager()
sliceWidget = lm.sliceWidget("Red")
sliceLogic = sliceWidget.sliceLogic()
volumeNode = sliceLogic.GetBackgroundLayer().GetVolumeNode()

print("Volume:", volumeNode.GetName())
print("Class:", volumeNode.GetClassName())

# ---- IJK → RAS 行列 ----
ijkToRas = vtk.vtkMatrix4x4()
volumeNode.GetIJKToRASMatrix(ijkToRas)

def ijk_to_ras(p):
    ras = [0, 0, 0, 1]
    ijkToRas.MultiplyPoint([p[0], p[1], p[2], 1.0], ras)
    return ras[:3]

points_ras = np.array([ijk_to_ras(p) for p in points_ijk])

# ---- Markups ----
fidNode = slicer.mrmlScene.AddNewNodeByClass(
    "vtkMRMLMarkupsFiducialNode",
    "Centerline_points_correct"
)

for p in points_ras:
    fidNode.AddControlPoint(p.tolist())

fidNode.GetDisplayNode().SetPointSize(6)
fidNode.GetDisplayNode().SetColor(1, 0, 0)

slicer.util.resetSliceViews()