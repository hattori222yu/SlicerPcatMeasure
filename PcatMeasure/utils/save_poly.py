# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 08:13:54 2025

@author: Hattori
"""
import vtk
def save_poly(save, polydata, path):
    if(save):
        writer = vtk.vtkPolyDataWriter()
        writer.SetInputData(polydata)
        writer.SetFileName(path)
        writer.Write()
    else:
        pass