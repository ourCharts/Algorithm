import numpy as np
import pandas as pd
import bisect
import pymysql
import math
from sklearn.cluster import KMeans
import os
from tqdm import tqdm
import matplotlib.pyplot as plt
from time import sleep

KAPPA = 24
K_T = 8
NODES_NUM_IN_TRANSITION_CALCULATION = 50
ITERATION_TIME = 3
spatial_cluster_centers = []
conn = pymysql.connect(host='localhost', user='root', port=3308,
                       passwd='', db='taxidb', charset='utf8')
cursor = conn.cursor(pymysql.cursors.SSCursor)


df = pd.read_csv('./data/node-list-updated.csv')
node_id = df.loc[:, 'real_id']
lon = df.loc[:, 'lon']
lat = df.loc[:, 'lat']
length = len(lon)
nodes = [(lon[i], lat[i], i, node_id[i]) for i in range(length)]
sorted_lon = sorted(lon)
sorted_lat = sorted(lat)
nodes_sorted_by_lon = nodes
nodes_sorted_by_lon = sorted(nodes_sorted_by_lon, key=lambda item: item[0])
nodes_sorted_by_lat = nodes
nodes_sorted_by_lat = sorted(nodes_sorted_by_lat, key=lambda item: item[1])

# spatial_cluster[i]中存的是所有属于第i个cluster的点的编号
spatial_cluster = [[] for i in range(200)]
transition_cluster = [[] for i in range(200)]    # 同上


def rad(deg):
    return (deg / 180.0) * math.pi 

EARTH_RADIUS = 6378.137


def get_distance(lon1, lat1, lon2, lat2):
    rad_lat1 = rad(lat1)
    rad_lat2 = rad(lat2)
    a = rad_lat1 - rad_lat2
    rad_lon1 = rad(lon1)
    rad_lon2 = rad(lon2)
    b = rad_lon2 - rad_lon1
    ret = 2 * math.asin(math.sqrt(math.pow(math.sin(a / 2), 2) +
                                  math.cos(rad_lat1) * math.cos(rad_lat2) * math.pow(math.sin(b / 2), 2)))
    ret *= EARTH_RADIUS
    ret = round(ret * 10000) / 10000
    return ret * 1000


def get_in_which_cluster(lon, lat):
    mindis = int(1e10)
    ret = -1
    for cluster_id ,center_it in enumerate(spatial_cluster_centers):
        dis = get_distance(lon, lat, center_it[0], center_it[1])
        if dis < mindis:
            mindis = dis
            ret = cluster_id
    return ret


# 通过一个网格, 得到距离某个经纬点最近的若干个订单开始点, 通过这些订单开始点近似计算这一经纬点的转移概率
def get_nodes_in_grid(lon, lat):
    lon_step = 0.00001141 * 50  # 5m
    lat_step = 0.00000899 * 50  # 5m
    ret = []
    while True:
        lef_lon = lon - lon_step
        rig_lon = lon + lon_step
        lower_lat = lat - lat_step
        upper_lat = lat + lat_step

        sql = 'SELECT * FROM myorder where start_longitude <= %f AND start_longitude >= %f AND start_latitude <= %f AND start_latitude >= %f' % (
            rig_lon, lef_lon, upper_lat, lower_lat)
        cursor.execute(sql)
        ret = cursor.fetchall()
        leng = len(ret)
        # print(leng)
        if leng < NODES_NUM_IN_TRANSITION_CALCULATION:
            lon_step += 0.00001141 * 5 
            lat_step += 0.00000899 * 5
        else:
            break
    return ret


def calculate_the_transition_probability():
    transition_probability = [(KAPPA + 2) * [0] for i in range(len(nodes))]  # B_ij 
    index_file = open('index_log.txt', 'a')
    for idx, node_item in tqdm(enumerate(nodes), desc='Calculating transition probabilities'):
        # if idx > 1: break
        node_lon = node_item[0]
        node_lat = node_item[1]
        ans = get_nodes_in_grid(node_lon, node_lat)
        ans_len = float(len(ans))
        probability = [0 for i in range(KAPPA + 2)]  # B_ij
        for ans_item in ans:
            end_lon = ans_item[5]
            end_lat = ans_item[6]
            in_which_cluster = get_in_which_cluster(end_lon, end_lat)
            index_file.write('%d\n' % in_which_cluster)
            probability[in_which_cluster] += 1
        for pro_idx, probability_item in enumerate(probability):
            probability[pro_idx] = float(probability[pro_idx])
            probability[pro_idx] = probability[pro_idx] / ans_len
        for j in range(len(transition_probability[idx])):
            transition_probability[idx][j] = probability[j]

    index_file.close()
    return transition_probability


def main():
    # 计算初始时的空间聚类
    spatial_sample = [[lon[i], lat[i]] for i in range(len(lon))]
    kkmeans = KMeans(n_clusters=KAPPA)
    y_pred = kkmeans.fit_predict(spatial_sample)
    for center_it in kkmeans.cluster_centers_:
        spatial_cluster_centers.append((center_it[0], center_it[1]))
    
    for idx, cluster_id in enumerate(y_pred):
        spatial_cluster[cluster_id].append(idx)
    
    for turn in tqdm(range(ITERATION_TIME), desc='Working...'):
        # 根据spatial cluster划分transition cluster
        last = 0
        probs = calculate_the_transition_probability()
        transition_sample = probs
        transition_pred = KMeans(n_clusters=K_T, random_state=900).fit_predict(transition_sample)
        with open('./data/transition_cluster_%d.txt' % turn, 'w+') as transition_cluster_file:
            for kk in transition_pred:
                transition_cluster_file.write('%d ' % kk)

        for item in transition_cluster:
            item.clear()
        # 聚类完成后, 将对应的点放到对应的list中
        for idx, item in enumerate(transition_pred):
            transition_cluster[item].append(idx)
        tmp_spatial_list = []
        for spatial_cluster_item in spatial_cluster:
            spatial_cluster_item.clear()

        # 对每一个transition cluster做一次空间聚类, 得到新的空间聚类
        spatial_cluster_centers.clear()
        for idx, item in enumerate(transition_cluster):
            if len(item) == 0: continue
            tmp_spatial_list.clear()
            for k in item:
                tmp_spatial_list.append(k)
            sub_spatial_sample = [[lon[i], lat[i]] for i in tmp_spatial_list]
            
            n = len(tmp_spatial_list)
            N = len(nodes)
            # size是每一个空间聚类的大小
            size = int(np.round(n * KAPPA / N))
            kmeans = KMeans(n_clusters=size, random_state=900)
            spatial_pred = kmeans.fit_predict(sub_spatial_sample)
            _centers = kmeans.cluster_centers_
            for center_it in _centers:
                spatial_cluster_centers.append((center_it[0], center_it[1]))
            
            
            # 对每一次空间聚类的出来的结果都要做偏移处理, 从而使得最终结果是正确的
            spatial_pred = [_item + last for _item in spatial_pred]
            last = max(spatial_pred) + 1

            for index in range(len(tmp_spatial_list)):
                spatial_cluster[spatial_pred[index]].append(tmp_spatial_list[index])


    # 输出结果, 可以用该结果来画图
    with open('./data/spatial-cluster.txt', 'w+') as f:
        for j, spatial_cluster_result_item in enumerate(spatial_cluster):
            f.write('%d :' % j)
            f.write('\n')
            for sub_item in spatial_cluster_result_item:
                f.write('%d ' % sub_item)
            f.write('\n')

    cursor.close()
    conn.close()

main()
