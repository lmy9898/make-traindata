#-*- coding:utf-8 -*-

import geopandas as gpd
import pandas as pd
import time
import json

# shape파일 경로
Dir_Path = 'C:/Users/test/Desktop/sentinel2 train/1km/'
shape = "shp/rice1_1km.shp"
# 이미지 경로
object = "img/"
Img_Name = "train_1km_"
#LAND_CODE
LAND_CODE = {'논' : 1, '밭' : 2, '시설' : 3, '인삼' : 4, '과수' : 5}

#shp파일 로드
df = gpd.read_file(Dir_Path + shape, encoding = 'utf-8')

# df = df.sort_values(["id_2"], ascending=[True]) # 이미지 순서대로 정렬
# df = df.iloc[:100]


#불필요한 열 제거
columns = ['left', 'top', 'right','bottom']
df.drop(columns, inplace=True, axis=1)
df['LAND_CODE'].value_counts(dropna = False)
df=df[df['LAND_CODE'] != '비경지']

# MultiPolygon 제거
tmp1 = df[df.geometry.type != 'MultiPolygon']
tmp2 = df[df.geometry.type == 'MultiPolygon']

df_1=gpd.GeoDataFrame()

n = 0
for ind in list(tmp2.index):
    for i in range(len(tmp2['geometry'][ind])):
        df_2 = gpd.GeoDataFrame({'LAND_CODE': [tmp2['LAND_CODE'][ind]],
                                 'id_2': [tmp2['id_2'][ind]],
                                 'geometry': [tmp2['geometry'][ind][i]]})
        n += 1

        df_1 = pd.concat([df_1, df_2])
# print(df_1)
# print(n)
# 두 데이터 프레임 결합
df=pd.concat([df_1,tmp1],sort=True)

# 인덱스 초기화
df = df.reset_index()
df.drop('index', inplace=True, axis=1)

# 이미지 파일 경로 추가
a = df.id_2.astype(int) -1
figname = Img_Name + a.astype(str)+'.tif'

df = df.assign(ID=df.index.astype(int),figname=figname, cd = Dir_Path + object + figname)
# df.drop('id_2', inplace=True, axis=1)

### 폴리곤 포인트 추출 ###
from osgeo import gdal

def pixel_xy(cd, mX, mY):
    gdata = gdal.Open(cd)
    gt = gdata.GetGeoTransform()
    (px, py) = gdal.ApplyGeoTransform(gdal.InvGeoTransform(gt), mX, mY)
    return int(px), int(py)

# LAND_CODE 넘버링

for k in LAND_CODE.keys():
    df.loc[df['LAND_CODE']==k, 'LAND_CODE'] = str(LAND_CODE[k])

t1 = time.time()
all_px = []
all_py = []

for id in list(df.ID):
  a = list(df.geometry[id].exterior.coords)
  pxy = [pixel_xy(df.cd[id],x,y) for x, y in a ]
  px = [ x for x, y in pxy ]
  py = [ y for x, y in pxy ]

  all_px.append(px)
  all_py.append(py)

temp_df = pd.DataFrame({"all_points_x": all_px, "all_points_y": all_py})

print(time.time() - t1)

df2=pd.concat([df,temp_df],axis=1)
columns = ['geometry','cd']
df2.drop(columns, inplace=True, axis=1)

df_train = df2

# train/val 데이터 분할
df_train = df2[df2.id_2 < 401]
df_val = df2[df2.id_2 >400]

### JSON 파일 생성 ###
def go2json(df2, dst):
    go2json = {}
    fignames = df2["figname"].unique().tolist()
    for name in fignames:
        # 이미지 범위 벚어 나는 값 전처리
        temp = df2.loc[df2["figname"] == name]

        # ID별로 X좌표와 Y좌표를 리스트로 묶어주기
        vX = temp['all_points_x']
        vY = temp['all_points_y']
        vName = temp['LAND_CODE']

        vName = vName.to_frame()

        # Dataframe으로 합치기
        df = pd.concat([vX, vY, vName], axis=1)

        shape_attributes = df.to_dict('records')

        regions = {
            str(idx): {"shape_attributes": {"all_points_x": val['all_points_x'], "all_points_y": val['all_points_y']}, \
                       "region_attributes": {"farm": val["LAND_CODE"]}} for idx, val in enumerate(shape_attributes)}

        # tif 파일이름 설정
        out = {"filename": name, "regions": regions}
        go2json[name] = out
    go2json = json.dumps(go2json)
    JSON_PATH = dst + "via_region_data.json"
    # JSON 파일로 쓰기
    with open(JSON_PATH, 'wt') as f:
        f.write(str(go2json))
dst_train = 'C:/Users/test/Desktop/sentinel2 train/1km/train_1km/'
dst_val = 'C:/Users/test/Desktop/sentinel2 train/1km/val_1km/'
go2json(df_train, dst_train)
go2json(df_val, dst_val)
# 

