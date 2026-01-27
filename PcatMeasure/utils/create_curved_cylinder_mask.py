# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 11:23:00 2025

@author: Hattori
"""
import vtk
from vtk.util import numpy_support
import numpy as np
def create_curved_cylinder_mask(branch_coords, branch_radius):
    

    points = vtk.vtkPoints()
    lines = vtk.vtkCellArray()

    for i, coord in enumerate(branch_coords):
        points.InsertNextPoint(coord)

    polyLine = vtk.vtkPolyLine()
    polyLine.GetPointIds().SetNumberOfIds(len(branch_coords))
    for i in range(len(branch_coords)):
        polyLine.GetPointIds().SetId(i, i)
    lines.InsertNextCell(polyLine)

    polyData = vtk.vtkPolyData()
    polyData.SetPoints(points)
    polyData.SetLines(lines)

    
    radius_array = numpy_support.numpy_to_vtk(branch_radius.astype(np.float32), deep=True)
    radius_array.SetName("TubeRadius")
    polyData.GetPointData().AddArray(radius_array)
    polyData.GetPointData().SetActiveScalars("TubeRadius")
                         
    
                         
    
    tubeFilter = vtk.vtkTubeFilter()
    tubeFilter.SetInputData(polyData)
    tubeFilter.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
    tubeFilter.SetNumberOfSides(20)  
    tubeFilter.CappingOn() 
    tubeFilter.Update()
    
                         
                         
    cleanFilter = vtk.vtkCleanPolyData()
    cleanFilter.SetInputConnection(tubeFilter.GetOutputPort())
    cleanFilter.Update()                     
    triangleFilter = vtk.vtkTriangleFilter()
    triangleFilter.SetInputConnection(cleanFilter.GetOutputPort())
    triangleFilter.Update()
    closed_polydata = triangleFilter.GetOutput()
                         
                      
    return closed_polydata    