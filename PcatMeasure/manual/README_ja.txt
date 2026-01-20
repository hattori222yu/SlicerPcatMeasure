### CoronaryCenterlineCrossSection

1. Load coronary CT image and centerline
2. Scroll along the centerline
3. Place or edit closed curves on cross-sectionsを修正したい。
次の日本語を英語に文脈も修正していいので作成してください。

もし、自前の冠動脈のセグメンテーションがない場合、解析領域の血管セグメンテーションを作成します。

1.[1]で冠動脈造影CT画像を選択してください。
２．手動で解析する枝の中心線を簡易的に作成し、[2]を選択してください。
３.もし必要なら次の係数を最初に調整してください。
step along centerline:中心線の点ごとに冠動脈の断面をセグメンテーションするのでその間の補間間隔。
circle resample points:６点で冠動脈の断面を囲むので、何点でclosed circleを作成するか。
smoothing kernel size：未定義
lumen kernel size:初期冠動脈セグメンテーションは閾値処理で簡易的に作成するので、そこから何倍のサイズでlumenサイズにするか。
４：[3]のapplyをすると中心線の点に沿って冠動脈の断面図が出ます。６点をそれぞれ調整し血管外壁を含めるように調整してください。
５:Red view画面でスクロールもしくはスライドバーでcenter line indexを動かし、すべての点に対して調整を行ってください。１回はすべての断面は確認してください。
６：[4}によって中心線にそって、修正済みの冠動脈のセグメンテーションが作成されます。
７：Go to PCAT MeasurementでPCAT解析モジュールに移動します。


### PcatMeasure
このモジュールには、造影CT画像と解析したい冠動脈のセグメンテーションが必要です。冠動脈のセグメンテーションは左と右にそれぞれ分かれていると解析しやすいです。
解析CT値範囲は-190～-30HUの平均値です。

１．データをどこからloadするかのチェックボックスです。デフォルトはSceneです。チェックを外すとファイルダイアログボックスから読み込めます。
2.解析する枝を選んでください。
３．CTvolumeとsegmentationを選択してください。CoronaryCenterlineCrossSectionのgo to pcatボタンから来た場合は、自動で入っています。
４．[1]:Get CT Nodeボタンをおしてください。
５．[2]を押して、解析する冠動脈の起始部にmarkedpointを設定してください。
６．PCATを計測する範囲のスライダーです。
デフォルトはRCAの場合起始部から10.0～50.0 mm、LAD,LCXの場合0.0～40.0 mmです。
7.[3]Select branchesを押して、冠動脈の高精度な中心線を取得します。チェックが入っているbranchが解析する枝になります。複数の枝がある場合は、解析したい枝のIDにしてください。解析に必要な長さになっているか確認してください。
８．[4]Analysis　PCATでPCAT領域のセグメンテーションを作成し解析します。python interactorもしくはouputディレクトリに.csvとしてPCATの値が表示・保存されます。

以下はoptionです。
・[5]:Show PCAT inflammationでカラーマップ化したPCAT領域が作成されます。
・Rest slicer viewsでreformatされたviewsが元に戻ります。
・Clear AllでSceneにあるデータをすべて削除します。
・Clear (except CT)でCT以外のデータをすべてSceneから削除します。RCAを解析し、次にLAD/LCXを解析するときに便利です。
・Back to Coronary Centerline Cross SectionはCoronary Centerline Cross Sectionモジュールに戻って、新たな解析ができます。