# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 13:38:58 2025

@author: fight
"""

#%%  
    def onLoadSegmentation2(self):
        import slicer
        filePath = qt.QFileDialog.getOpenFileName(
            None,
            "Select segmentation file",
            "",
            "Segmentation files (*.seg.nrrd *.nii *.nii.gz *.nrrd);;All files (*)"
        )

        if not filePath:
            slicer.util.infoDisplay("No segmentation file selected.")
            return

        self.segPathLabel.setText(f"Segmentation: {filePath}")
        img = nib.load(filePath)
        affine = img.affine
        
        
        
        case_id = '00000000'
        segmentName = 'Segment_1'
        targetClass="left"
        
        endpointName = f"Endpoints_{case_id}_{targetClass}"
        endpointmodelName = f"Endptmodel_{case_id}_{targetClass}"
        centermodelName = f"Model_{case_id}_{targetClass}"
        voronoimodelName = f"Voronoi_{case_id}_{targetClass}"
        centertableName = f"Properties_{case_id}_{targetClass}"
        centercurveName = f"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      _"
        
        # 保存先フォルダ
         
        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir=os.path.join(base_dir,"output")
        # フォルダがなければ作成
        os.makedirs(save_dir, exist_ok=True)
        # ファイルパス
        save_path = os.path.join(save_dir, "01_inputSurfacePolyData.vtk")
        
        
        # Slicer add node
        endpointModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", endpointmodelName)
        centerlineModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", centermodelName)
        voronoiModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", voronoimodelName)
        centerlinePropertiesTableNode =  slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode" ,centertableName)
        centerlineCurveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", centercurveName)
        
        #球体を非表示
        #centerlineCurveNode.GetDisplayNode().SetVisibility(False)

        # Step1: Load Segmentation: From Path to 'vtkMRMLSegmentationNode' type        
        print("step1")
        print(filePath)
        #seg_path = f"{serverPath}\{case_id}\{segmentationName}" # Specific to my dataset 
        #seg_path = "E:/coronary_data_600/1.label.nii.gz" # Specific to my dataset 
        seg_path=filePath
        segmentationNode = slicer.util.loadSegmentation(seg_path)
        segmentID = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)

        #from vmtk.ExtractCenterline import ExtractCenterline
        extractLogic = ExtractCenterline_slicer.ExtractCenterlineLogic()

        # Step2: SegmentationNode to vtkPolyData
        print("step2")
        inputSurfacePolyData = extractLogic.polyDataFromNode(segmentationNode, segmentID)
        #print('DEBUG', inputSurfacePolyData)
        SAVE_VTK=True
        save_poly(SAVE_VTK, inputSurfacePolyData, os.path.join(save_dir, "01_inputSurfacePolyData.vtk"))
                 
               
        
        targetNumberOfPoints = 5000.0
        decimationAggressiveness = 4 # I had to lower this to 3.5 in at least one case to get it to work, 4 is the default in the module
        subdivideInputSurface = False
        preprocessedPolyData = extractLogic.preprocess(inputSurfacePolyData, targetNumberOfPoints, decimationAggressiveness, subdivideInputSurface)
        save_poly(SAVE_VTK, preprocessedPolyData, os.path.join(save_dir, "02_preprocessedPolyData.vtk"))
        
        # Step3: Extract Centerline Network (Approximated Centerline)
        print("step3")
        endPointsMarkupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", endpointName)
        #非表示
        endPointsMarkupsNode.GetDisplayNode().SetVisibility(False)
        networkPolyData = extractLogic.extractNetwork(preprocessedPolyData, endPointsMarkupsNode, computeGeometry=True)  # Voronoi 
        
        
        
        # Create Centerline Model
        endpointModelNode.SetAndObserveMesh(networkPolyData)

        # Step4: Get EndPoints ( AutoDetect )
        print("step4")
        startPointPosition=None
        endpointPositions = extractLogic.getEndPoints(networkPolyData, startPointPosition) # AutoDetect the endpoints. type: List
        endPointsMarkupsNode.RemoveAllControlPoints()
        for position in endpointPositions:
            endPointsMarkupsNode.AddControlPoint(vtk.vtkVector3d(position))

        # Step5: Extract Centerline, Voronoi
        centerlinePolyData, voronoiDiagramPolyData = extractLogic.extractCenterline(preprocessedPolyData, endPointsMarkupsNode)
        centerlineModelNode.SetAndObserveMesh(centerlinePolyData)          
        voronoiModelNode.SetAndObserveMesh(voronoiDiagramPolyData)  

        # Step6: Extract centerlineCurves
        mergedCenterlines, centerlineProperties, cell_pt = extractLogic.createCurveTreeFromCenterline(centerlinePolyData, centerlineCurveNode, centerlinePropertiesTableNode) 
            
        save_poly(SAVE_VTK, mergedCenterlines, os.path.join(save_dir,"06_mergedCenterlines.vtk"))
        
        
        
        
        #####################################################
        # Preliminary for the Radius Calculation in each curve
        #各セル（枝）ごとの点IDを取得
        #mergedCenterlines の各セル（曲線単位）に含まれる 点のインデックスリスト を保存
        #後で、曲線ごとの点列の抽出や幾何量の関連付けに使う
        #####################################################
        self.cell_pt = {}
        for cell in range(mergedCenterlines.GetNumberOfCells()):
            self.cell_pt[cell] = []
            getCell = mergedCenterlines.GetCell(cell)
            for idx in range(getCell.GetPointIds().GetNumberOfIds()):
                pt = getCell.GetPointIds().GetId(idx)
                self.cell_pt[cell].append(pt)
    
        # Step7: Extract centerlineCurve info
        print("step7")
        SAVE_INFO = True
        if(SAVE_INFO):
            r1 = mergedCenterlines.GetPointData().GetArray('Radius')
            #print(r1)
            radius_arr = vtk.util.numpy_support.vtk_to_numpy(r1)    
            #print(radius_arr)
            
            with open(os.path.join(save_dir,'centerCurve_radius.pickle'), 'wb') as f:
                pickle.dump(radius_arr, f, pickle.HIGHEST_PROTOCOL)

            properties_dict = {}
            for columnName in [extractLogic.lengthArrayName, extractLogic.curvatureArrayName, extractLogic.torsionArrayName, extractLogic.tortuosityArrayName]:
                vtk_arr = centerlineProperties.GetPointData().GetArray(columnName)
                properties_dict[columnName] = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            with open(os.path.join(save_dir,'centerCurve_property_dict.pickle'), 'wb') as f:
                pickle.dump(properties_dict, f, pickle.HIGHEST_PROTOCOL)
                
            #print(cell_pt)
            with open(os.path.join(save_dir,'centerCurve_cell_idx.pickle'), 'wb') as f:
                pickle.dump(cell_pt, f, pickle.HIGHEST_PROTOCOL)

            vtk_arr = mergedCenterlines.GetPoints().GetData()
            array = vtk.util.numpy_support.vtk_to_numpy(vtk_arr)
            coord_mm = {}
            coord_voxel = {}
            for cell in cell_pt:
                cell_array = array[self.cell_pt[cell]]
                coord_mm[cell] = cell_array
                coord_voxel[cell] = apply_affine(np.linalg.inv(affine), array[cell_pt[cell]])
            with open(os.path.join(save_dir,'centerCurve_coord_mm.pickle'), 'wb') as f:
                pickle.dump(coord_mm, f, pickle.HIGHEST_PROTOCOL)
            with open(os.path.join(save_dir,'centerCurve_coord_voxel.pickle'), 'wb') as f:
                pickle.dump(coord_voxel, f, pickle.HIGHEST_PROTOCOL)

        
        groupIdsArrayName = 'GroupIds'
        groupIdsArray = mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
        print("----------------------------------")
        #print("gropuIdsArray",groupIdsArray)
        print("----------------------------------")
        
        # 2. ユニークな GroupIds を取得
        uniqueGroupIds = list(set(groupIdsArray.GetTuple1(i) for i in range(groupIdsArray.GetNumberOfTuples())))
        #print("uG",uniqueGroupIds)
        #uniqueGroupIds.sort()  # 一応順番揃える
        numGroups = len(uniqueGroupIds)
        
        
        
        
        
        
        #get branch
        branch_id = []

        total_lengths = []
        for i in range(mergedCenterlines.GetNumberOfCells()):
            points_branch = coord_mm[i]  # shape = (N, 3)            
            diffs = np.diff(points_branch, axis=0)
            segment_lengths = np.linalg.norm(diffs, axis=1)
            total_length = np.sum(segment_lengths)
            #print("i",i,"total_length",total_length)
            total_lengths.append(total_length)
        self.coronary_artery_name="RCA"
        if self.coronary_artery_name == "RCA":
            cumulative_length = 0
            for i in range(len(total_lengths)):
                cumulative_length += total_lengths[i]
                branch_id.append(i)
                if cumulative_length >= 50:
                    break
        #branch_id はとりあえず自動で選んだPCAT領域に対応するID
        print("branch_id",branch_id)
        
        
        
        #CT画像上で取得した起始部の座標を取得###################################################
        print("aaaaaa")
        # Markupsノードを取得
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("PickedPoints")
        if not markupsNode:
            slicer.util.warningDisplay("No markups found. Please enable markups and place points first.")
            return
    
        n = markupsNode.GetNumberOfFiducials()
        if n == 0:
            slicer.util.warningDisplay("No points placed yet.")
            return
    
        coordinates = []
        for i in range(n):
            ras = [0.0, 0.0, 0.0]
            markupsNode.GetNthFiducialPosition(i, ras)
            coordinates.append(ras)
            print(f"Point {i+1}: R={ras[0]:.2f}, A={ras[1]:.2f}, S={ras[2]:.2f}")
    
        # 出力例：メッセージで全座標をまとめて表示
        msg = "\n".join([f"P{i+1}: {r[0]:.2f}, {r[1]:.2f}, {r[2]:.2f}" for i, r in enumerate(coordinates)])
        slicer.util.infoDisplay(f"Picked Points (RAS):\n{msg}")
        
        ##########################################################
    
    
    
    
    
        ##############元のコードから．長さとかIDを表示   VIL=>view_id_lengthの略
        group_ids = mergedCenterlines.GetCellData().GetArray(groupIdsArrayName)
        #print("group_ids",group_ids)
        points = mergedCenterlines.GetPoints()
        vivid_colors = [(1, 0, 0),(0, 1, 0),(0, 0, 1),(1, 1, 0),(1, 0, 1),(0, 1, 1),(1, 0.5, 0),(0.5, 0, 1),
                         (1, 0, 0.5),(0.5, 0.5, 0),(0, 0.5, 1),(0, 1, 0.5),(0.5, 1, 0), (1, 0.25, 0),(0.25, 0, 1),
                        (0, 1, 0.25),(0.75, 0, 1),(1, 0, 0.75),(0.5, 1, 1),(1, 1, 0.5)]
        for i in range(mergedCenterlines.GetNumberOfCells()):
            cell_VIL = mergedCenterlines.GetCell(i)
            group_VIL = group_ids.GetValue(i)
            branch_id_VIL = uniqueGroupIds.index(group_VIL)
            
            # 差分をとってユークリッド距離を計算
            points_branch_VIL  = coord_mm[i]  # shape = (N, 3)            
            diffs_VIL = np.diff(points_branch_VIL, axis=0)  # 連続する点の差分ベクトル（N-1, 3）
            segment_lengths_VIL = np.linalg.norm(diffs_VIL, axis=1)  # 各セグメントの長さ
            total_length_VIL = np.sum(segment_lengths_VIL)  # 合計
         
            # ブランチの中点のインデックスを取得
            mid_index_VIL = cell_VIL.GetNumberOfPoints() // 2
            point_id_VIL = cell_VIL.GetPointId(mid_index_VIL)
            position_VIL = points.GetPoint(point_id_VIL)
            
            text_source = vtk.vtkVectorText()
            text_source.SetText(f"     {branch_id_VIL} [{total_length_VIL:.1f}mm]")
            
            # 厚みを付ける
            extrude = vtk.vtkLinearExtrusionFilter()
            extrude.SetInputConnection(text_source.GetOutputPort())
            extrude.SetExtrusionTypeToNormalExtrusion()
            extrude.SetVector(0,0,1)
            extrude.SetScaleFactor(0.5)
            extrude.Update()
            
            text_mapper = vtk.vtkPolyDataMapper()
            text_mapper.SetInputConnection(extrude.GetOutputPort())
            
            text_actor = vtk.vtkFollower()
            text_actor.SetMapper(text_mapper)
            text_actor.GetProperty().SetColor(vivid_colors[i])
            text_actor.GetProperty().SetAmbient(0.5)
            text_actor.GetProperty().SetDiffuse(0.5)
            text_actor.SetScale(4, 4, 4)
            text_actor.SetPosition(position_VIL)
            
            renderer = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer()
            renderer.AddActor(text_actor)
            
            camera = renderer.GetActiveCamera()
            text_actor.SetCamera(camera)
            
            # アンチエイリアス強化
            slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().SetMultiSamples(8)
            renderer.ResetCameraClippingRange()
            slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().Render()
            
                        
                        
                        
            
        #enabled, selected = chk_branch.showRadioPopup(total_lengths,branch_id,self.coronary_artery_name)    
        #print("enabled",enabled,"select",selected)
        
        selected_ids, total_selected_length = showMultiCheckPopup(total_lengths,branch_id,self.coronary_artery_name)
        print("Selected branches:", selected_ids,"Total length:", total_selected_length,"now artery is ",self.coronary_artery_name,"coordiante",coordinates[0])
        print("coordiante",coordinates[0][0],coordinates[0][1],coordinates[0][2])
        ####################################################################
        #どこを起始部とするかの座標をGUIとかで取得→それがpoints_culmulative_voxelで一番近い座標を探索→、それが配列で何番目かのインデックスか
        #調べて,points_culmulative_mmのほうに値としていれる→実装しました。
        ####################################################################
        print("now cal start point ")
        points_culmulative_mm =  np.concatenate([coord_mm[i] for i in selected_ids], axis=0)#coord_mm[self.branch_id]  # shape = (N, 3)
        points_culmulative_voxel =  np.concatenate([coord_voxel[i] for i in selected_ids], axis=0)#coord_voxel[self.branch_id]  # shape = (N, 3)
        #[abs(x) for x in coordinates[0]]でマイナスの値を絶対値化⇒したらだめでした．
        #[203,365,132]
        test_cood=[203,365,132]
        
        ###############################
        #coordinates変数はRASorLAS座標．
        #points_culmulative_voxelはIJK座標なので変換が必要
        ###############################
        ras_point = coordinates[0]  # [-14.61, 204.66, 105.45]
        
        # RAS→IJK行列を取得
        rasToIJK = vtk.vtkMatrix4x4()
        self.ctNode.GetRASToIJKMatrix(rasToIJK)
        
        # 同次座標で計算
        ijk_h = [0, 0, 0, 1]
        rasToIJK.MultiplyPoint([ras_point[0], ras_point[1], ras_point[2], 1], ijk_h)
        
        # 最初の3つが IJK
        ijk = ijk_h[:3]
        print("IJK (float):", ijk)
        
        # 必要なら整数にする
        ijk_int = [round(v) for v in ijk]
        print("IJK (int):", ijk_int)
        print("test",test_cood)
        #RAS 形式
        #start_corrdinate=cal_start_point(coordinates[0],points_culmulative_voxel) 
        
        #IJK　形式
        start_corrdinate=cal_start_point(ijk_int,points_culmulative_voxel)
        
        
        print("start_corrdinate",start_corrdinate)
        
        ##2行目はテスト
        
        points_culmulative=points_culmulative_mm[start_corrdinate:,:]
        #points_culmulative=points_culmulative_mm[10:,:]
 
        #print("points_culmulative",points_culmulative)
        
        # 各点の差分ベクトル（連続する点の移動）
        diffs_culmulative = np.diff(points_culmulative, axis=0)  # (N-1, 3)

        # 各区間の長さ（ユークリッド距離）
        segment_lengths_culmulative = np.linalg.norm(diffs_culmulative, axis=1)  # (N-1,)

        # 累積距離の配列：先頭に0を付けて [0, d1, d1+d2, ...]
        cumulative_distances = np.insert(np.cumsum(segment_lengths_culmulative), 0, 0.0)  # shape = (N,)
        if self.coronary_artery_name=="RCA":
            mask_PCAT = (cumulative_distances >= 10.0) & (cumulative_distances <= 50.0)
        else:
            mask_PCAT = (cumulative_distances >= 0.0) & (cumulative_distances <= 40.0)
            
        # まず各branchのpoint idリストを順番に取り出して
        lists = [self.cell_pt[bid] for bid in branch_id]
        # それらをまとめて1次元のnumpy配列にする
        #point_ids = np.array(self.cell_pt[self.branch_id])  # 　←だとself.branch_idはリストなのでエラー
        point_ids = np.array([pid for sublist in lists for pid in sublist])  # 　←だと分岐のところの点が重複している。多分重複はよくなさそう       
            
        #####################################################################    いるかふめい
        #① VTKの点群データと累積長さを取得
        #reader = vtk.vtkPolyDataReader()
        #reader.SetFileName('C:/Users/Hattori/SegmentationViewer/output/06_mergedCenterlines.vtk')
        #reader.Update()
        #mergedCenterlines = reader.GetOutput()
        points_vtk_array = mergedCenterlines.GetPoints().GetData()
        self.points_np = vtk.util.numpy_support.vtk_to_numpy(points_vtk_array)
        
        point_ids_after_start_selected_=point_ids[start_corrdinate:]

        # ③ 区間を絞る（10〜20mm）
        ###########################################
        selected_ids2 = point_ids_after_start_selected_[mask_PCAT]


        #print("selected_ids",selected_ids)
        #print("冠動脈:",str(self.coronary_artery_name),"の選ばれたID",selected_ids[0],"-",selected_ids[-1])
        #cumulative_distance_maskはただprintするためだけの変数
        cumulative_distance_mask=cumulative_distances[mask_PCAT]
        
        if selected_ids2.shape[0] < 2:
            raise ValueError("need two point data")
            
        ############################################
        # ④ 新しい vtkPoints と polyLine を作る
        ############################################
        new_points = vtk.vtkPoints()
        new_lines = vtk.vtkCellArray()
                             
        ############################################
        #print("最終的に抽出した点の数(10-50mm or 0-40mmの範囲)",selected_ids.shape)                     
        # ⑤ 点を登録
        ############################################
        id_map = {}  # 元のpoint_id → 新しい順番
        for i, pid in enumerate(selected_ids2):
            #print(i,pid)
            coord = self.points_np[pid]
            new_points.InsertNextPoint(coord)
            id_map[pid] = i    
            
        # ⑥ polyline作成（直線的な連続接続）
        ############################################
        line = vtk.vtkPolyLine()
        line.GetPointIds().SetNumberOfIds(len(selected_ids2))
        for i in range(len(selected_ids2)):
            line.GetPointIds().SetId(i, i)
        new_lines.InsertNextCell(line)
        ############################################
        # ⑦ vtkPolyData に登録
        ############################################
        self.new_polydata = vtk.vtkPolyData()
        self.new_polydata.SetPoints(new_points)
        self.new_polydata.SetLines(new_lines)
        ############################################
        # ⑧ vtkとPCATを測定する範囲をvtkとして保存
        ############################################
        writer = vtk.vtkPolyDataWriter()
        if self.coronary_artery_name=="RCA":

            writer.SetFileName(os.path.join(save_dir,f"07branch{branch_id}_{self.coronary_artery_name}_10to50mm.vtk"))
        else:
            writer.SetFileName(os.path.join(save_dir,f"07branch{branch_id}_{self.coronary_artery_name}_0to40mm.vtk"))
        writer.SetInputData(self.new_polydata)
        writer.Write()
        print("finish")
        ##################################################################################################################################
        #　ここからextract pcat2
        ##################################################################################################################################
        #radius_arr=>radius_data
        #cell_pt=>cell_id_data
        
        radius_data=radius_arr
        cell_id_data=cell_pt
        lists = [cell_id_data[bid] for bid in branch_id]
        branch_id_list = np.array([pid for sublist in lists for pid in sublist])  
        branch_0_coords_all = self.points_np[branch_id_list]
        branch_0_radius_all = radius_data[branch_id_list]
        branch_0_coords=branch_0_coords_all[start_corrdinate:,:]
        branch_0_radius=branch_0_radius_all[start_corrdinate:]
        
        branch_0_coords_PCAT=branch_0_coords[mask_PCAT]
        branch_0_radius_PCAT=branch_0_radius[mask_PCAT]  
        
        
        
        
        
        # === RAS → IJK 変換 ===
        
        ##################元のコードはこれ
        #coord_mm = np.hstack([branch_0_coords_PCAT, np.ones((len(branch_0_coords_PCAT), 1))])
        #coord_voxel = (inv_affine @ coord_mm.T).T[:, :3]
        #coord_voxel = np.round(coord_voxel).astype(int)
        #coord_voxel=np.abs(coord_voxel)
        ##################
        ras_to_ijk = vtk.vtkMatrix4x4()
        self.ctNode.GetRASToIJKMatrix(ras_to_ijk)
        
        def ras_to_ijk_np(points_ras):
            ijk_list = []
            for p in points_ras:
                dst = [0,0,0,0]
                vtk.vtkMatrix4x4.MultiplyPoint(ras_to_ijk, [p[0], p[1], p[2], 1], dst)
                ijk_list.append(dst[:3])
            return np.round(np.array(ijk_list)).astype(int)
        
        coord_voxel = ras_to_ijk_np(branch_0_coords_PCAT)
                
                            
        #半径に応じた血管とPCAT領域を作成．なお，tubepolyデータはModelデータになっている
        tube_polydata = create_curved_cylinder_mask(branch_0_coords_PCAT, branch_0_radius_PCAT*3.0)
        print("Tube Points:", tube_polydata.GetNumberOfPoints())  # ← 0でないこと
                   
        #vtk_image_1x = self.polydata_to_mask2(tube_polydata, self.spacing, self.origin, self.image_size)
        #self.save_vtk_image_as_nifti(vtk_image_1x, self.spacing, self.origin, f"./{self.SAVE_PATH}/pcat_mask_new.nii.gz")
        
        # 書き出し
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(os.path.join(save_dir,f"08_{self.coronary_artery_name}_PCAT_Coronary_Wall.vtk"))
        writer.SetInputData(tube_polydata)
        writer.Write()
        
        
        
        
        #######################################
        
        # tube_polydata は RAS 座標の PolyData
        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        modelNode.SetAndObservePolyData(tube_polydata)
        modelNode.SetName("seg_artery_PCAT")
        
        
        segNode_artery_PCAT = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "TubeSegmentation")
        # セグメンテーションの座標系を CT と合わせる（RAS）
        segNode_artery_PCAT.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        # モデルをセグメントとして追加
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(
            modelNode, segNode_artery_PCAT
            )         
        ##ここまでOK!
        # ---------------------------------------------------
        # 1) 新しい SegmentationNode に2つを結合
        # ---------------------------------------------------
        seg_artery=segmentationNode
        mergedSeg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "MergedSeg")
        mergedSeg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        logic = slicer.modules.segmentations.logic()
        
        # 2) A -> LabelMap にエクスポート
        labelA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        # ExportAllSegmentsToLabelmapNode か ExportVisibleSegmentsToLabelmapNode のどちらか環境で使える方を
        # 
        try:
            logic.ExportAllSegmentsToLabelmapNode(seg_artery, labelA, self.ctNode)
        except Exception:
            logic.ExportVisibleSegmentsToLabelmapNode(seg_artery, labelA, self.ctNode)
        print("Exported seg_artery ->", labelA.GetName(), labelA.GetID())
        
        # 3) B -> LabelMap にエクスポート
        labelB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        try:
            logic.ExportAllSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)
        except Exception:
            logic.ExportVisibleSegmentsToLabelmapNode(segNode_artery_PCAT, labelB, self.ctNode)
        print("Exported segNode_artery_PCAT ->", labelB.GetName(), labelB.GetID())

        logic.ImportLabelmapToSegmentationNode(labelA, mergedSeg)
        print("Imported labelA into mergedSeg")
        
        # 5) labelB を mergedSeg に import
        logic.ImportLabelmapToSegmentationNode(labelB, mergedSeg)
        print("Imported labelB into mergedSeg")
        
        # 6) 確認：mergedSeg の segment list を表示
        seg = mergedSeg.GetSegmentation()
        ids = seg.GetSegmentIDs()
        print("Merged segments:")
        for sid in ids:
            print("  ID:", sid, "Name:", seg.GetSegment(sid).GetName())
                        
        segmentIdA = "Segment_1"
        segmentIdB = "seg_artery_PCAT"
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorNode.SetAndObserveSegmentationNode(mergedSeg)
        segmentEditorNode.SetAndObserveMasterVolumeNode(self.ctNode)
        
        # SUBTRACT 設定
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        
              
        
        
        # —— SUBTRACT: B − A ——
        segmentEditorNode.SetSelectedSegmentID(segmentIdB)
        segmentEditorNode.SetActiveEffectName("Logical operators")
        
        effect = segmentEditorWidget.activeEffect()
        if effect is None:
            raise RuntimeError("Logical operators effect not available.")
        
        effect.setParameter("Operation", "SUBTRACT")
        effect.setParameter("ModifierSegmentID", segmentIdA)
        
        # APPLY
        effect.self().onApply()
        slicer.app.processEvents()
        
        # クリーンアップ
        segmentEditorWidget = None
        print("After SUBTRACT:")
        for i in range(seg.GetNumberOfSegments()):
            segID = seg.GetNthSegmentID(i)
            print(" ", segID, " -> ", seg.GetSegment(segID).GetName())
            
        #############################################################ここまでOK!
        
        
        PCAT_seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "PCAT_seg")
        PCAT_seg.SetReferenceImageGeometryParameterFromVolumeNode(self.ctNode)
        
        # ---- 2) 抽出したい segment ID を指定（mergedSeg の中） ----
        segmentIdB = "seg_artery_PCAT"
        
        # ---- 3) segment → labelmap ----
        labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "tempLabel")
        
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
            mergedSeg,              # source segmentation
            [segmentIdB],           # segment ID list
            labelNode,              # target labelmap
            self.ctNode             # reference volume
        )
        
        # ---- 4) labelmap → 新しい segmentation へインポート ----
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            labelNode,
            PCAT_seg
        )
        
        print("PCAT_seg created with segment:", segmentIdB)
        
        
        # ---- 5) 不要な labelNode を削除 ----
        slicer.mrmlScene.RemoveNode(labelA)
        slicer.mrmlScene.RemoveNode(labelB)
        slicer.mrmlScene.RemoveNode(labelNode)
        slicer.mrmlScene.RemoveNode(mergedSeg)
        displayNode = segNode_artery_PCAT.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility(False)  
        
        ct_values = getCTvaluesFromSegmentation(PCAT_seg, self.ctNode)
        print("Voxel count:", len(ct_values))
        print("Mean HU:", np.mean(ct_values))
        print("Std HU:", np.std(ct_values))
        hu_min = -190
        hu_max = -30
        
        # ct_values はセグメント内ボクセルの HU 値が入った 1D numpy 配列
        masked_values = ct_values[(ct_values >= hu_min) & (ct_values <= hu_max)]
        
        if masked_values.size == 0:
            mean_hu = None   # 該当値がない場合
        else:
            mean_hu = masked_values.mean()
        print("PCAT HU:", mean_hu)
        
        do_save_overlay=False
        overlay_dir = os.path.join(save_dir, "overlay")
        os.makedirs(overlay_dir, exist_ok=True)
        if do_save_overlay==True:
            print("now save overlay")
            labelNode = exportSegToLabel(PCAT_seg, self.ctNode)
            #saveOverlayImage(self.ctNode, labelNode)
            if self.saveOverlayCheckBox.checked:
                saveOverlayImage(
                    self.ctNode,
                    labelNode,
                    outputDir=overlay_dir
                )
            
        
    