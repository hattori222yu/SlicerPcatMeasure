# -*- coding: utf-8 -*-
"""
Created on Wed Jan 14 16:39:30 2026

@author: fight
"""


import vtk
import slicer
import numpy as np
from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic
import logging

#
# ExtractCenterlineLogic
#

class ExtractCenterlineLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.blankingArrayName = 'Blanking'
        self.radiusArrayName = 'Radius'  # maximum inscribed sphere radius
        self.groupIdsArrayName = 'GroupIds'
        self.centerlineIdsArrayName = 'CenterlineIds'
        self.tractIdsArrayName = 'TractIds'
        self.topologyArrayName = 'Topology'
        self.marksArrayName = 'Marks'
        self.lengthArrayName = 'Length'
        self.curvatureArrayName = 'Curvature'
        self.torsionArrayName = 'Torsion'
        self.tortuosityArrayName = 'Tortuosity'
        self.frenetTangentArrayName = 'FrenetTangent'
        self.frenetNormalArrayName = 'FrenetNormal'
        self.frenetBinormalArrayName = 'FrenetBinormal'

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        # We choose a small target point number value, so that we can get fast speed
        # for smooth meshes. Actual mesh size will mainly determined by DecimationAggressiveness value.
        if not parameterNode.GetParameter("TargetNumberOfPoints"):
            parameterNode.SetParameter("TargetNumberOfPoints", "5000")
        if not parameterNode.GetParameter("DecimationAggressiveness"):
            parameterNode.SetParameter("DecimationAggressiveness", "4.0")
        if not parameterNode.GetParameter("PreprocessInputSurface"):
            parameterNode.SetParameter("PreprocessInputSurface", "true")
        if not parameterNode.GetParameter("SubdivideInputSurface"):
            parameterNode.SetParameter("SubdivideInputSurface", "false")
        if not parameterNode.GetParameter("CurveSamplingDistance"):
            parameterNode.SetParameter("CurveSamplingDistance", "1.0")

    def polyDataFromNode(self, surfaceNode, segmentId):
        if not surfaceNode:
            logging.error("Invalid input surface node")
            return None
        if surfaceNode.IsA("vtkMRMLModelNode"):
            return surfaceNode.GetPolyData()
        elif surfaceNode.IsA("vtkMRMLSegmentationNode"):
            # Segmentation node
            polyData = vtk.vtkPolyData() # a geometric structure consisting of vertices, lines, polygons, and/or triangle strips.
            surfaceNode.CreateClosedSurfaceRepresentation() # Generate closed surface representation for all segments ( 3D visualization purpose)
            surfaceNode.GetClosedSurfaceRepresentation(segmentId, polyData) # Get a segment as binary labelmap.
            return polyData
        else:
            logging.error("Surface can only be loaded from model or segmentation node")
            return None

    def preprocess(self, surfacePolyData, targetNumberOfPoints, decimationAggressiveness, subdivide):
        # import the vmtk libraries
        try:
            import vtkvmtkComputationalGeometryPython as vtkvmtkComputationalGeometry
            import vtkvmtkMiscPython as vtkvmtkMisc
        except ImportError:
            raise ImportError("VMTK library is not found")

        numberOfInputPoints = surfacePolyData.GetNumberOfPoints()
        if numberOfInputPoints == 0:
            raise("Input surface model is empty")
        reductionFactor = (numberOfInputPoints-targetNumberOfPoints) / numberOfInputPoints
        if reductionFactor > 0.0:
            parameters = {}
            inputSurfaceModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "tempInputSurfaceModel")
            inputSurfaceModelNode.SetAndObserveMesh(surfacePolyData)
            parameters["inputModel"] = inputSurfaceModelNode
            outputSurfaceModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "tempDecimatedSurfaceModel")
            parameters["outputModel"] = outputSurfaceModelNode
            parameters["reductionFactor"] = reductionFactor
            parameters["method"] = "FastQuadric"
            parameters["aggressiveness"] = decimationAggressiveness
            decimation = slicer.modules.decimation
            cliNode = slicer.cli.runSync(decimation, None, parameters)
            surfacePolyData = outputSurfaceModelNode.GetPolyData()
            slicer.mrmlScene.RemoveNode(inputSurfaceModelNode)
            slicer.mrmlScene.RemoveNode(outputSurfaceModelNode)
            slicer.mrmlScene.RemoveNode(cliNode)

        surfaceCleaner = vtk.vtkCleanPolyData()
        surfaceCleaner.SetInputData(surfacePolyData)
        surfaceCleaner.Update()

        surfaceTriangulator = vtk.vtkTriangleFilter()
        surfaceTriangulator.SetInputData(surfaceCleaner.GetOutput())
        surfaceTriangulator.PassLinesOff()
        surfaceTriangulator.PassVertsOff()
        surfaceTriangulator.Update()

        # new steps for preparation to avoid problems because of slim models (f.e. at stenosis)
        if subdivide:
            subdiv = vtk.vtkLinearSubdivisionFilter()
            subdiv.SetInputData(surfaceTriangulator.GetOutput())
            subdiv.SetNumberOfSubdivisions(1)
            subdiv.Update()
            if subdiv.GetOutput().GetNumberOfPoints() == 0:
                logging.warning("Mesh subdivision failed. Skip subdivision step.")
                subdivide = False

        normals = vtk.vtkPolyDataNormals()
        if subdivide:
            normals.SetInputData(subdiv.GetOutput())
        else:
            normals.SetInputData(surfaceTriangulator.GetOutput())
        normals.SetAutoOrientNormals(1)
        normals.SetFlipNormals(0)
        normals.SetConsistency(1)
        normals.SplittingOff()
        normals.Update()

        return normals.GetOutput()

    def extractNonManifoldEdges(self, polyData, nonManifoldEdgesPolyData=None):
        '''
        Returns non-manifold edge center positions.
        nonManifoldEdgesPolyData: optional vtk.vtkPolyData() input, if specified then a polydata is returned that contains the edges
        '''
        import vtkvmtkDifferentialGeometryPython as vtkvmtkDifferentialGeometry
        neighborhoods = vtkvmtkDifferentialGeometry.vtkvmtkNeighborhoods()
        neighborhoods.SetNeighborhoodTypeToPolyDataManifoldNeighborhood()
        neighborhoods.SetDataSet(polyData)
        neighborhoods.Build()

        polyData.BuildCells()
        polyData.BuildLinks(0)

        edgeCenterPositions = []

        neighborCellIds = vtk.vtkIdList()
        nonManifoldEdgeLines = vtk.vtkCellArray()
        points = polyData.GetPoints()
        for i in range(neighborhoods.GetNumberOfNeighborhoods()):
            neighborhood = neighborhoods.GetNeighborhood(i)
            for j in range(neighborhood.GetNumberOfPoints()):
                neighborId = neighborhood.GetPointId(j)
                if i < neighborId:
                    neighborCellIds.Initialize()
                    polyData.GetCellEdgeNeighbors(-1, i, neighborId, neighborCellIds)
                    if neighborCellIds.GetNumberOfIds() > 2:
                        nonManifoldEdgeLines.InsertNextCell(2)
                        nonManifoldEdgeLines.InsertCellPoint(i)
                        nonManifoldEdgeLines.InsertCellPoint(neighborId)
                        p1 = points.GetPoint(i)
                        p2 = points.GetPoint(neighborId)
                        edgeCenterPositions.append([(p1[0]+p2[0])/2.0, (p1[1]+p2[1])/2.0, (p1[2]+p2[2])/2.0])

        if nonManifoldEdgesPolyData:
            pointsCopy = vtk.vtkPoints()
            pointsCopy.DeepCopy(polyData.GetPoints())
            nonManifoldEdgesPolyData.SetPoints(pointsCopy)
            nonManifoldEdgesPolyData.SetLines(nonManifoldEdgeLines)

        return edgeCenterPositions

    def startPointIndexFromEndPointsMarkupsNode(self, endPointsMarkupsNode):
        """Return start point index from endpoint markups node.
        Endpoint is the first unselected control point. If none of them is unselected then
        the first control point.
        """
        numberOfControlPoints = endPointsMarkupsNode.GetNumberOfControlPoints()
        if numberOfControlPoints == 0:
            return -1
        for controlPointIndex in range(numberOfControlPoints):
            if not endPointsMarkupsNode.GetNthControlPointSelected(controlPointIndex):
                # Found a non-selected node, this is the starting point
                return controlPointIndex
        # All points are selected, use the first one as start point
        return 0

    def extractNetwork(self, surfacePolyData, endPointsMarkupsNode, computeGeometry=False):
        """
        Extract centerline network from surfacePolyData
        :param surfacePolyData: input surface
        :param endPointsMarkupsNode: markup node containing preferred branch starting point
        :return: polydata containing vessel centerlines
        """
        import vtkvmtkComputationalGeometryPython as vtkvmtkComputationalGeometry
        import vtkvmtkMiscPython as vtkvmtkMisc

        # Decimate
        # It seems that decimation at this stage is not necessary (decimation in preprocessing is enough).
        # By not decimating here, we can keep th network and centerline extraction results more similar.
        # If network extraction is too slow then one can experiment with this flag.
        decimate = False
        if decimate:
            decimationFilter = vtk.vtkDecimatePro()
            decimationFilter.SetInputData(surfacePolyData)
            decimationFilter.SetTargetReduction(0.99)
            decimationFilter.SetBoundaryVertexDeletion(0)
            decimationFilter.PreserveTopologyOn()
            decimationFilter.Update()

        # Clean and triangulate
        cleaner = vtk.vtkCleanPolyData() # Merge duplicate points, and/or remove unused points and/or remove degenerate cells (in: polygonal data, out: polygonal data)
        if decimate:
            cleaner.SetInputData(decimationFilter.GetOutput())
        else:
            cleaner.SetInputData(surfacePolyData) # Assign a data object as input.
        triangleFilter = vtk.vtkTriangleFilter() # Convert input polygons and strips to triangles
        triangleFilter.SetInputConnection(cleaner.GetOutputPort()) #OutputPort: Get a proxy object corresponding to the given output port of this algorithm.
        triangleFilter.Update()
        simplifiedPolyData = triangleFilter.GetOutput() # type: vtkPolyData

        # Cut hole at start position
        if endPointsMarkupsNode and endPointsMarkupsNode.GetNumberOfControlPoints() > 0: # ControlPoint가 주어진 경우
            startPosition = [0, 0, 0]
            endPointsMarkupsNode.GetNthControlPointPosition(
                self.startPointIndexFromEndPointsMarkupsNode(endPointsMarkupsNode), startPosition)
        else: # AutoDetection 원리: point closest to a corner
            # If no endpoints are specific then use the closest point to a corner
            bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            simplifiedPolyData.GetBounds(bounds) # 주어진 polyData에 해당하는 x,y,z 범위를 bound에 update함. Return a pointer to the geometry bounding box in the form (xmin,xmax, ymin,ymax, zmin,zmax). 
            startPosition = [bounds[0], bounds[2], bounds[4]] # 말 그대로 시작점.
        self.openSurfaceAtPoint(simplifiedPolyData, startPosition) # startPoisition 에서 가장 가까운 point를 찾고 해당 point에 연결된 CellId 중 첫 번째 Cell을 PolyData로부터 삭제한다 (why?)

        # Extract network: An approximated network graph (preliminary to centerline)
        # http://www.vmtk.org/vmtkscripts/vmtknetworkextraction.html
        networkExtraction = vtkvmtkMisc.vtkvmtkPolyDataNetworkExtraction() # Extract a network of approximated centerlines from a surface, the surface must have at least an opening
        networkExtraction.SetInputData(simplifiedPolyData) # input: vtkPolyData
        networkExtraction.SetAdvancementRatio(1.05) # the ratio between the sphere step and the local maximum radius
        networkExtraction.SetRadiusArrayName(self.radiusArrayName)
        networkExtraction.SetTopologyArrayName(self.topologyArrayName)
        networkExtraction.SetMarksArrayName(self.marksArrayName)
        networkExtraction.Update()


        if computeGeometry:
            centerlineGeometry = vtkvmtkComputationalGeometry.vtkvmtkCenterlineGeometry()
            centerlineGeometry.SetInputData(networkExtraction.GetOutput()) # input: vtkPolyData
            centerlineGeometry.SetLengthArrayName(self.lengthArrayName)
            centerlineGeometry.SetCurvatureArrayName(self.curvatureArrayName)
            centerlineGeometry.SetTorsionArrayName(self.torsionArrayName)
            centerlineGeometry.SetTortuosityArrayName(self.tortuosityArrayName)
            centerlineGeometry.SetFrenetTangentArrayName(self.frenetTangentArrayName)
            centerlineGeometry.SetFrenetNormalArrayName(self.frenetNormalArrayName)
            centerlineGeometry.SetFrenetBinormalArrayName(self.frenetBinormalArrayName)
            # centerlineGeometry.SetLineSmoothing(0)
            # centerlineGeometry.SetOutputSmoothedLines(0)
            # centerlineGeometry.SetNumberOfSmoothingIterations(100)
            # centerlineGeometry.SetSmoothingFactor(0.1)
            centerlineGeometry.Update()
            return centerlineGeometry.GetOutput() # output: vtkPolyData
        else:
            return networkExtraction.GetOutput() # output: vtkPolyData

    def extractCenterline(self, surfacePolyData, endPointsMarkupsNode, curveSamplingDistance=1.0):
        """Compute centerline.
        This is more robust and accurate but takes longer than the network extraction.
        :param surfacePolyData:
        :param endPointsMarkupsNode:
        :return:
        """

        import vtkvmtkComputationalGeometryPython as vtkvmtkComputationalGeometry
        import vtkvmtkMiscPython as vtkvmtkMisc

        # Cap all the holes that are in the mesh that are not marked as endpoints
        # Maybe this is not needed.
        capDisplacement = 0.0
        surfaceCapper = vtkvmtkComputationalGeometry.vtkvmtkCapPolyData()
        surfaceCapper.SetInputData(surfacePolyData)
        surfaceCapper.SetDisplacement(capDisplacement)
        surfaceCapper.SetInPlaneDisplacement(capDisplacement)
        surfaceCapper.Update()

        if not endPointsMarkupsNode or endPointsMarkupsNode.GetNumberOfControlPoints() < 2:
            raise ValueError("At least two endpoints are needed for centerline extraction")

        tubePolyData = surfaceCapper.GetOutput()
        pos = [0.0, 0.0, 0.0]
        # It seems that vtkvmtkComputationalGeometry does not need holes (unlike network extraction, which does need one hole)
        # # Punch holes at surface endpoints to have tubular structure
        # tubePolyData = surfaceCapper.GetOutput()
        # numberOfEndpoints = endPointsMarkupsNode.GetNumberOfControlPoints()
        # for pointIndex in range(numberOfEndpoints):
        #     endPointsMarkupsNode.GetNthControlPointPosition(pointIndex, pos)
        #     self.openSurfaceAtPoint(tubePolyData, pos)

        numberOfControlPoints = endPointsMarkupsNode.GetNumberOfControlPoints()
        foundStartPoint = False
        for controlPointIndex in range(numberOfControlPoints):
            if not endPointsMarkupsNode.GetNthControlPointSelected(controlPointIndex): # Get the Selected flag on the Nth control point, returns false if control point doesn't exist
                foundStartPoint = True
                break

        sourceIdList = vtk.vtkIdList()
        targetIdList = vtk.vtkIdList()

        pointLocator = vtk.vtkPointLocator()
        pointLocator.SetDataSet(tubePolyData)
        pointLocator.BuildLocator()

        for controlPointIndex in range(numberOfControlPoints):
            isTarget = endPointsMarkupsNode.GetNthControlPointSelected(controlPointIndex)
            if not foundStartPoint and controlPointIndex == 0:
                # If no start point found then use the first point as source
                isTarget = False
            endPointsMarkupsNode.GetNthControlPointPosition(controlPointIndex, pos)
            # locate the point on the surface
            pointId = pointLocator.FindClosestPoint(pos)
            if isTarget:
                targetIdList.InsertNextId(pointId)
            else:
                sourceIdList.InsertNextId(pointId)

        slicer.tubePolyData = tubePolyData

        centerlineFilter = vtkvmtkComputationalGeometry.vtkvmtkPolyDataCenterlines()
        centerlineFilter.SetInputData(tubePolyData)
        centerlineFilter.SetSourceSeedIds(sourceIdList)
        centerlineFilter.SetTargetSeedIds(targetIdList)
        centerlineFilter.SetRadiusArrayName(self.radiusArrayName)
        centerlineFilter.SetCostFunction('1/R')  # this makes path search prefer go through points with large radius
        centerlineFilter.SetFlipNormals(False)
        centerlineFilter.SetAppendEndPointsToCenterlines(0)

        # Voronoi smoothing slightly improves connectivity
        # Unfortunately, Voronoi smoothing is broken if VMTK is used with VTK9, therefore
        # disable this feature for now (https://github.com/vmtk/SlicerExtension-VMTK/issues/34)
        enableVoronoiSmoothing = (slicer.app.majorVersion * 100 + slicer.app.minorVersion < 413) # False
        centerlineFilter.SetSimplifyVoronoi(enableVoronoiSmoothing)

        centerlineFilter.SetCenterlineResampling(0)
        centerlineFilter.SetResamplingStepLength(curveSamplingDistance)
        centerlineFilter.Update()

        centerlinePolyData = vtk.vtkPolyData()
        centerlinePolyData.DeepCopy(centerlineFilter.GetOutput())

        voronoiDiagramPolyData = vtk.vtkPolyData()
        voronoiDiagramPolyData.DeepCopy(centerlineFilter.GetVoronoiDiagram())

        logging.debug("End of Centerline Computation..")
        return centerlinePolyData, voronoiDiagramPolyData

    def openSurfaceAtPoint(self, polyData, holePosition=None, holePointIndex=None):
        '''
        Modifies the polyData by cutting a hole at the given position.
        '''

        if holePointIndex is None:
            pointLocator = vtk.vtkPointLocator() # Quickly locate points in 3-space. 
            #Dividing a specified region of space into a regular array of "rectangular" buckets, 
            # and then keeping a list of points that lie in each bucket. 
            # Typical operation involves giving a position in 3D and finding the closest point.

            pointLocator.SetDataSet(polyData) # Build the locator from the points/cells defining this dataset.
            pointLocator.BuildLocator() # Build the locator from the input dataset.
            # find the closest point to the desired hole position
            holePointIndex = pointLocator.FindClosestPoint(holePosition) #  Given a position x (startPosition), return the id of the point closest to it.

        if holePointIndex < 0:
            # Calling GetPoint(-1) would crash the application
            raise ValueError("openSurfaceAtPoint failed: empty input polydata")

        # Tell the polydata to build 'upward' links from points to cells
        polyData.BuildLinks()
        # Mark cells as deleted
        cellIds = vtk.vtkIdList()
        polyData.GetPointCells(holePointIndex, cellIds) # Efficient method to obtain cells using a particular point. (Make sure that routine BuildLinks() has been called.)
        removeFirstCell = True
        if removeFirstCell:
            # remove first cell only (smaller hole)
            if cellIds.GetNumberOfIds() > 0:
                polyData.DeleteCell(cellIds.GetId(0))
                polyData.RemoveDeletedCells()
        else:
            # remove all cells
            for cellIdIndex in range(cellIds.GetNumberOfIds()):
                polyData.DeleteCell(cellIds.GetId(cellIdIndex))
            polyData.RemoveDeletedCells()

    def getEndPoints(self, inputNetworkPolyData, startPointPosition):
        '''
        Clips the surfacePolyData on the endpoints identified using the networkPolyData.
        If startPointPosition is specified then start point will be the closest point to that position.
        Returns list of endpoint positions. Largest radius point is be the first in the list.
        '''
        try:
            import vtkvmtkComputationalGeometryPython as vtkvmtkComputationalGeometry
            import vtkvmtkMiscPython as vtkvmtkMisc
        except ImportError:
            logging.error("Unable to import the SlicerVmtk libraries")

        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputData(inputNetworkPolyData)
        cleaner.Update()
        network = cleaner.GetOutput() # vtkPolyData
        network.BuildCells() # Create data structure that allows random access of cells.
        network.BuildLinks(0) # Create upward links from points to cells that use each point. (0: Initial Size)

        networkPoints = network.GetPoints() # vtkPoints
        radiusArray = network.GetPointData().GetArray(self.radiusArrayName) # vtkTypeFloat64Array

        startPointId = -1
        maxRadius = 0
        minDistance2 = 0

        endpointIds = vtk.vtkIdList()
        for i in range(network.GetNumberOfCells()): # ex) Network에는 총 11개의 Cell이 존재했고
            numberOfCellPoints = network.GetCell(i).GetNumberOfPoints() # ex) 각 cell 마다 보유한 Point의 수만큼 for-loop를 돌면서 
            if numberOfCellPoints < 2:
                continue

            for pointIndex in [0, numberOfCellPoints - 1]:
                pointId = network.GetCell(i).GetPointId(pointIndex)
                pointCells = vtk.vtkIdList()
                network.GetPointCells(pointId, pointCells) # ex) 각 Cell의 각 point 마다 연결된 Cell의 수를 측정하여 Unique한 경우 radius를 비교해본다
                if pointCells.GetNumberOfIds() == 1:
                    endpointIds.InsertUniqueId(pointId)
                    if startPointPosition is not None:
                        # find start point based on position
                        position = networkPoints.GetPoint(pointId)
                        distance2 = vtk.vtkMath.Distance2BetweenPoints(position, startPointPosition)
                        if startPointId < 0 or distance2 < minDistance2:
                            minDistance2 = distance2
                            startPointId = pointId
                    else:
                        # find start point based on radius
                        radius = radiusArray.GetValue(pointId)
                        if startPointId < 0 or radius > maxRadius:
                            maxRadius = radius 
                            startPointId = pointId

        endpointPositions = []
        numberOfEndpointIds = endpointIds.GetNumberOfIds() # 예시) 총 7개의 unique한 (한 cell에만 포함된) point가 있었다.
        if numberOfEndpointIds == 0:
            return endpointPositions
        # add the largest radius point first
        endpointPositions.append(networkPoints.GetPoint(startPointId)) # startPointID 를 시작으로
        # add all the other points
        for pointIdIndex in range(numberOfEndpointIds): # Unique한 endpoint들을 endpoint로 삼는다
            pointId = endpointIds.GetId(pointIdIndex)
            if pointId == startPointId:
                # already added
                continue
            endpointPositions.append(networkPoints.GetPoint(pointId))

        return endpointPositions

    def createCurveTreeFromCenterline(self, centerlinePolyData, centerlineCurveNode=None, centerlinePropertiesTableNode=None, curveSamplingDistance=1.0):

        import vtkvmtkComputationalGeometryPython as vtkvmtkComputationalGeometry

        branchExtractor = vtkvmtkComputationalGeometry.vtkvmtkCenterlineBranchExtractor() # Split and group centerlines.
        branchExtractor.SetInputData(centerlinePolyData)
        branchExtractor.SetBlankingArrayName(self.blankingArrayName)
        branchExtractor.SetRadiusArrayName(self.radiusArrayName)
        branchExtractor.SetGroupIdsArrayName(self.groupIdsArrayName)
        branchExtractor.SetCenterlineIdsArrayName(self.centerlineIdsArrayName)
        branchExtractor.SetTractIdsArrayName(self.tractIdsArrayName)
        branchExtractor.Update()
        centerlines = branchExtractor.GetOutput() # type: vtkPolyData

        writer = vtk.vtkPolyDataWriter()
        writer.SetInputData(centerlines)
        writer.SetFileName("./test_centerlines.vtk")
        writer.Write()

        mergeCenterlines = vtkvmtkComputationalGeometry.vtkvmtkMergeCenterlines()
        mergeCenterlines.SetInputData(centerlines)
        mergeCenterlines.SetRadiusArrayName(self.radiusArrayName)
        mergeCenterlines.SetGroupIdsArrayName(self.groupIdsArrayName)
        mergeCenterlines.SetCenterlineIdsArrayName(self.centerlineIdsArrayName)
        mergeCenterlines.SetTractIdsArrayName(self.tractIdsArrayName)
        mergeCenterlines.SetBlankingArrayName(self.blankingArrayName)
        mergeCenterlines.SetResamplingStepLength(curveSamplingDistance)
        mergeCenterlines.SetMergeBlanked(True)
        mergeCenterlines.Update()
        mergedCenterlines = mergeCenterlines.GetOutput() # type: vtkPolyData

        writer = vtk.vtkPolyDataWriter()
        writer.SetInputData(mergedCenterlines)
        writer.SetFileName("./test_mergedCenterlines.vtk")
        writer.Write()


        # Preliminary for the Radius Calculation for each curve
        cell_pt = {}
        for cell in range(mergedCenterlines.GetNumberOfCells()):
            cell_pt[cell] = []
            getCell = mergedCenterlines.GetCell(cell)
            for idx in range(getCell.GetPointIds().GetNumberOfIds()):
                pt = getCell.GetPointIds().GetId(idx)
                cell_pt[cell].append(pt)
        

        if centerlinePropertiesTableNode:
            centerlinePropertiesTableNode.RemoveAllColumns()

            # Cell index column
            numberOfCells = mergedCenterlines.GetNumberOfCells() # ex) 10
            cellIndexArray = vtk.vtkIntArray()
            cellIndexArray.SetName("CellId")
            cellIndexArray.SetNumberOfValues(numberOfCells)
            for cellIndex in range(numberOfCells):
                cellIndexArray.SetValue(cellIndex, cellIndex)
            centerlinePropertiesTableNode.GetTable().AddColumn(cellIndexArray)


            # Get average radius
            pointDataToCellData = vtk.vtkPointDataToCellData()
            pointDataToCellData.SetInputData(mergedCenterlines)
            pointDataToCellData.ProcessAllArraysOff()
            pointDataToCellData.AddPointDataArray(self.radiusArrayName)
            pointDataToCellData.Update()
            averageRadiusArray = pointDataToCellData.GetOutput().GetCellData().GetArray(self.radiusArrayName)
            centerlinePropertiesTableNode.GetTable().AddColumn(averageRadiusArray)

            # Get length, curvature, torsion, tortuosity
            centerlineBranchGeometry = vtkvmtkComputationalGeometry.vtkvmtkCenterlineBranchGeometry()
            centerlineBranchGeometry.SetInputData(mergedCenterlines)
            centerlineBranchGeometry.SetRadiusArrayName(self.radiusArrayName)
            centerlineBranchGeometry.SetGroupIdsArrayName(self.groupIdsArrayName)
            centerlineBranchGeometry.SetBlankingArrayName(self.blankingArrayName)
            centerlineBranchGeometry.SetLengthArrayName(self.lengthArrayName)
            centerlineBranchGeometry.SetCurvatureArrayName(self.curvatureArrayName)
            centerlineBranchGeometry.SetTorsionArrayName(self.torsionArrayName)
            centerlineBranchGeometry.SetTortuosityArrayName(self.tortuosityArrayName)
            centerlineBranchGeometry.SetLineSmoothing(False)
            #centerlineBranchGeometry.SetNumberOfSmoothingIterations(100)
            #centerlineBranchGeometry.SetSmoothingFactor(0.1)
            centerlineBranchGeometry.Update()
            centerlineProperties = centerlineBranchGeometry.GetOutput() # type: vtkPolyData
            for columnName in [self.lengthArrayName, self.curvatureArrayName, self.torsionArrayName, self.tortuosityArrayName]:
                centerlinePropertiesTableNode.GetTable().AddColumn(centerlineProperties.GetPointData().GetArray(columnName))

            # Get branch start and end positions
            startPointPositions = vtk.vtkDoubleArray()
            startPointPositions.SetName("StartPointPosition")
            endPointPositions = vtk.vtkDoubleArray()
            endPointPositions.SetName("EndPointPosition")
            for positions in [startPointPositions, endPointPositions]:
                positions.SetNumberOfComponents(3)
                positions.SetComponentName(0, "R")
                positions.SetComponentName(1, "A")
                positions.SetComponentName(2, "S")
                positions.SetNumberOfTuples(numberOfCells)
            for cellIndex in range(numberOfCells):
                pointIds = mergedCenterlines.GetCell(cellIndex).GetPointIds()
                startPointPosition = [0, 0, 0]
                if pointIds.GetNumberOfIds() > 0:
                    mergedCenterlines.GetPoint(pointIds.GetId(0), startPointPosition)
                if pointIds.GetNumberOfIds() > 1:
                    endPointPosition = [0, 0, 0]
                    mergedCenterlines.GetPoint(pointIds.GetId(pointIds.GetNumberOfIds()-1), endPointPosition)
                else:
                    endPointPosition = startPointPosition
                startPointPositions.SetTuple3(cellIndex, *startPointPosition)
                endPointPositions.SetTuple3(cellIndex, *endPointPosition)
            centerlinePropertiesTableNode.GetTable().AddColumn(startPointPositions)
            centerlinePropertiesTableNode.GetTable().AddColumn(endPointPositions)

            centerlinePropertiesTableNode.GetTable().Modified()

        if centerlineCurveNode:
            self.addCenterlineCurves(mergedCenterlines, centerlineCurveNode)

        return mergedCenterlines, centerlineProperties, cell_pt

    def addCenterlineCurves(self, mergedCenterlines, centerlineCurveNode):
        # Delete existing children of the output markups curve
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        curveItem = shNode.GetItemByDataNode(centerlineCurveNode)
        shNode.RemoveItemChildren(curveItem)
        # Add centerline widgets
        self.processedCellIds = []
        self._addCenterline(mergedCenterlines, replaceCurve=centerlineCurveNode)

    def _addCurveMeasurementArray(self, curveNode, radiusArray):
        try:
            # Add radius as curve measurement
            radiusMeasurement = curveNode.GetMeasurement(radiusArray.GetName())
            if not radiusMeasurement:
                radiusMeasurement = slicer.vtkMRMLStaticMeasurement()
                radiusMeasurement.SetName(radiusArray.GetName())
                radiusMeasurement.SetUnits('mm')
                radiusMeasurement.SetPrintFormat('') # Prevent from showing up in subject hierarchy Description column
                radiusMeasurement.SetControlPointValues(radiusArray)
                curveNode.AddMeasurement(radiusMeasurement)
            else:
                radiusMeasurement.SetControlPointValues(radiusArray)
        except:
            # This Slicer version does not support curve measurements
            pass

    def _addCenterline(self, mergedCenterlines, baseName=None, cellId=0, parentItem=None, replaceCurve=None):
        # Add current cell as a curve node
        assignAttribute = vtk.vtkAssignAttribute()
        assignAttribute.SetInputData(mergedCenterlines)
        assignAttribute.Assign(self.groupIdsArrayName, vtk.vtkDataSetAttributes.SCALARS,
                               vtk.vtkAssignAttribute.CELL_DATA)
        thresholder = vtk.vtkThreshold()
        thresholder.SetInputConnection(assignAttribute.GetOutputPort())
        groupId = mergedCenterlines.GetCellData().GetArray(self.groupIdsArrayName).GetValue(cellId)
        #thresholder.ThresholdBetween(groupId - 0.5, groupId + 0.5)
        thresholder.SetLowerThreshold(groupId - 0.5)
        thresholder.SetUpperThreshold(groupId + 0.5)

        thresholder.Update()

        if replaceCurve:
            # update existing curve widget
            curveNode = replaceCurve
            if baseName is None:
                baseName = curveNode.GetName()
                # Parse name, if it ends with a number in a parenthesis ("branch (1)") then assume it contains
                # the cell index and remove it to get the base name
                import re
                matched = re.match(r"(.+) \([0-9]+\)", baseName)
                if matched:
                    baseName = matched[1]
            curveNode.SetName("{0} ({1})".format(baseName, cellId))
        else:
            if baseName is None:
                baseName = "branch"
            curveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", "{0} ({1})".format(baseName, cellId))
            curveNode.CreateDefaultDisplayNodes()
            colorNode = slicer.mrmlScene.GetNodeByID("vtkMRMLColorTableNodeRandom")
            color = [0.5, 0.5, 0.5, 1.0]
            colorNode.GetColor(cellId, color)
            curveNode.GetDisplayNode().SetSelectedColor(color[0:3])
            curveNode.SetNumberOfPointsPerInterpolatingSegment(1)

        curveNode.SetAttribute("CellId", str(cellId))
        curveNode.SetAttribute("GroupId", str(groupId))
        curveNode.SetControlPointPositionsWorld(thresholder.GetOutput().GetPoints())

        self._addCurveMeasurementArray(curveNode, thresholder.GetOutput().GetPointData().GetArray('Radius'))

        slicer.modules.markups.logic().SetAllControlPointsVisibility(curveNode, False)
        slicer.app.processEvents()
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        curveItem = shNode.GetItemByDataNode(curveNode)
        if parentItem is not None:
            shNode.SetItemParent(curveItem, parentItem)
        # Add connecting cells
        self.processedCellIds.append(cellId)
        cellPoints = mergedCenterlines.GetCell(cellId).GetPointIds()
        endPointIndex = cellPoints.GetId(cellPoints.GetNumberOfIds() - 1)
        numberOfCells = mergedCenterlines.GetNumberOfCells()
        branchIndex = 0
        for neighborCellIndex in range(numberOfCells):
            if neighborCellIndex in self.processedCellIds:
                continue
            if endPointIndex != mergedCenterlines.GetCell(neighborCellIndex).GetPointIds().GetId(0):
                continue
            branchIndex += 1
            self._addCenterline(mergedCenterlines, baseName, neighborCellIndex, curveItem)

    def addNetworkProperties(self, networkPolyData, networkPropertiesTableNode):
        networkPropertiesTableNode.RemoveAllColumns()

        # Cell index column
        numberOfCells = networkPolyData.GetNumberOfCells()
        cellIndexArray = vtk.vtkIntArray()
        cellIndexArray.SetName("CellId")
        cellIndexArray.SetNumberOfValues(numberOfCells)
        for cellIndex in range(numberOfCells):
            cellIndexArray.SetValue(cellIndex, cellIndex)
        networkPropertiesTableNode.GetTable().AddColumn(cellIndexArray)

        # Add length
        lengthArray = networkPolyData.GetCellData().GetArray(self.lengthArrayName)
        if not lengthArray:
            raise ValueError("Network polydata does not contain length cell array")
        networkPropertiesTableNode.GetTable().AddColumn(lengthArray)

        # Add average radius, curvature, torsion values
        for columnName in [self.radiusArrayName, self.curvatureArrayName, self.torsionArrayName]:
            pointDataToCellData = vtk.vtkPointDataToCellData()
            pointDataToCellData.SetInputData(networkPolyData)
            pointDataToCellData.ProcessAllArraysOff()
            pointDataToCellData.AddPointDataArray(columnName)
            pointDataToCellData.Update()
            averageArray = pointDataToCellData.GetOutput().GetCellData().GetArray(columnName)
            if not averageArray:
                raise ValueError("Failed to compute array " + columnName)
            networkPropertiesTableNode.GetTable().AddColumn(averageArray)

        # Add tortuosity
        tortuosityArray = networkPolyData.GetCellData().GetArray(self.tortuosityArrayName)
        if not tortuosityArray:
            raise ValueError("Network polydata does not contain length cell array")
        networkPropertiesTableNode.GetTable().AddColumn(tortuosityArray)

        # Add branch start and end positions
        startPointPositions = vtk.vtkDoubleArray()
        startPointPositions.SetName("StartPointPosition")
        endPointPositions = vtk.vtkDoubleArray()
        endPointPositions.SetName("EndPointPosition")
        for positions in [startPointPositions, endPointPositions]:
            positions.SetNumberOfComponents(3)
            positions.SetComponentName(0, "R")
            positions.SetComponentName(1, "A")
            positions.SetComponentName(2, "S")
            positions.SetNumberOfTuples(numberOfCells)
        for cellIndex in range(numberOfCells):
            pointIds = networkPolyData.GetCell(cellIndex).GetPointIds()
            startPointPosition = [0, 0, 0]
            if pointIds.GetNumberOfIds() > 0:
                networkPolyData.GetPoint(pointIds.GetId(0), startPointPosition)
            if pointIds.GetNumberOfIds() > 1:
                endPointPosition = [0, 0, 0]
                networkPolyData.GetPoint(pointIds.GetId(pointIds.GetNumberOfIds()-1), endPointPosition)
            else:
                endPointPosition = startPointPosition
            startPointPositions.SetTuple3(cellIndex, *startPointPosition)
            endPointPositions.SetTuple3(cellIndex, *endPointPosition)
        networkPropertiesTableNode.GetTable().AddColumn(startPointPositions)
        networkPropertiesTableNode.GetTable().AddColumn(endPointPositions)

        networkPropertiesTableNode.GetTable().Modified()


    def addNetworkCurves(self, networkPolyData, centerlineCurveNode, baseName=None):
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        parentItem = shNode.GetItemByDataNode(centerlineCurveNode)

        # remove old children
        shNode.RemoveItemChildren(parentItem)

        if baseName is None:
            baseName = centerlineCurveNode.GetName()

        colorNode = slicer.mrmlScene.GetNodeByID("vtkMRMLColorTableNodeRandom")
        numberOfCells = networkPolyData.GetNumberOfCells()
        slicer.app.pauseRender()
        try:
            radiusArray = networkPolyData.GetPointData().GetArray('Radius')
            for cellId in range(numberOfCells):
                # Create curve node
                curveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", "{0} ({1})".format(baseName, cellId))
                curveNode.CreateDefaultDisplayNodes()
                color = [0.5, 0.5, 0.5, 1.0]
                colorNode.GetColor(cellId, color)
                curveNode.GetDisplayNode().SetSelectedColor(color[0:3])
                curveNode.SetNumberOfPointsPerInterpolatingSegment(1)
                # Add to subject hierarchy
                curveItem = shNode.GetItemByDataNode(curveNode)
                shNode.SetItemParent(curveItem, parentItem)

                # Add point positions and radius array
                radiusMeasurementArray = vtk.vtkDoubleArray()
                radiusMeasurementArray.SetName('Radius')
                curveNode.SetAttribute("CellId", str(cellId))
                cellPoints = networkPolyData.GetCell(cellId).GetPointIds()
                numberOfCellCurvePoints = cellPoints.GetNumberOfIds()
                for cellPointIdIndex in range(numberOfCellCurvePoints):
                    pointId = cellPoints.GetId(cellPointIdIndex)
                    curveNode.AddControlPointWorld(vtk.vtkVector3d(networkPolyData.GetPoint(pointId)))
                    radiusMeasurementArray.InsertNextValue(radiusArray.GetValue(pointId))

                self._addCurveMeasurementArray(curveNode, radiusMeasurementArray)

                slicer.modules.markups.logic().SetAllMarkupsVisibility(curveNode, False)
        finally:
            slicer.app.resumeRender()
