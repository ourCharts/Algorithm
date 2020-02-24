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

KAPPA = 64
K_T = 20
conn = pymysql.connect(host='localhost', user='root', port=3308,
                       passwd='', db='taxidb', charset='utf8')
cursor = conn.cursor(pymysql.cursors.SSCursor)

# 从数据库中得到一个order记录
def get_an_order(idx):
    sql = 'SELECT start_longitude, start_latitude, end_longitude, end_latitude FROM myorder LIMIT %d, 1' % (
        idx - 1)
    cursor.execute(sql)
    ret = cursor.fetchall()
    return ret[0]


# info = get_an_order(1)

df = pd.read_csv('./data/node-list.csv')
node_id = df.loc[:, 'real_id']
# cluster_id = df.loc[:, 'cluster_id']
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

def process_out_of_range(pos):
    leng = len(sorted_lat)
    if pos < 0:
        pos += 1
    if pos >= leng:
        pos -= 1
    return pos

# 计算与某个经纬点距离最近的路口点, 返回结果对应的nodeid
def get_closest_node(lon, lat):
    min_distance = int(1e10)
    real_id_val = -1
    lsh_id_val = -1
    """for idx, item in enumerate(nodes):
        distance = get_distance(item[0], item[1], lon, lat)
        if distance < min_distance:
            min_distance = distance
            real_id_val = item[3]
            lsh_id_val = idx
    return real_id_val, lsh_id_val, min_distance"""
    lon_step = 0.00001141 * 20  # 20m
    lat_step = 0.00000899 * 20  # 20m
    tmp_list = []
    while True:
        lefbnd = bisect.bisect_left(sorted_lon, lon - lon_step)
        lefbnd = process_out_of_range(lefbnd)
        
        rigbnd = bisect.bisect_right(sorted_lon, lon + lon_step)
        rigbnd = process_out_of_range(rigbnd)
        
        upbnd = bisect.bisect_right(sorted_lat, lat + lat_step)
        upbnd = process_out_of_range(upbnd)
        
        downbnd = bisect.bisect_left(sorted_lat, lat - lat_step)
        downbnd = process_out_of_range(downbnd)
        tmp_list.clear()
        for ii in range(lefbnd, rigbnd + 1):
            if nodes_sorted_by_lon[ii][1] <= sorted_lat[upbnd] and nodes_sorted_by_lon[ii][1] >= sorted_lat[downbnd]:
                tmp_list.append(nodes_sorted_by_lon[ii])
        if len(tmp_list) != 0:
            break
        else:
            lon_step += 0.00001141 * 10
            lat_step += 0.00000899 * 10
    for idx, item in enumerate(tmp_list):
        distance = get_distance(item[0], item[1], lon, lat)
        if distance < min_distance:
            min_distance = distance
            real_id_val = item[3]
            lsh_id_val = item[2]
    return real_id_val, lsh_id_val, min_distance

# 计算某个经纬点位于哪一个cluster中(该经纬点来自于order, 不在nodes中)
def get_in_which_cluster(lon, lat):
    # print('lon = %f, lat = %f' % (lon, lat))
    closest_node_real_id, closest_node_lsh_id, mindis = get_closest_node(
        lon, lat)
    # print('mindis = %f, closest_node_lsh_id = %f, closest_node_real_id = %f' % (mindis, closest_node_lsh_id, closest_node_real_id))
    for k in range(len(spatial_cluster)):
        if closest_node_lsh_id in spatial_cluster[k]:
            return k
    print("Can't find in which cluster!")


# 通过一个网格, 得到距离某个经纬点最近的若干个订单开始点, 通过这些订单开始点近似计算这一经纬点的转移概率
def get_nodes_in_grid(lon, lat):
    lon_step = 0.00001141 * 5  # 5m
    lat_step = 0.00000899 * 5  # 5m
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
        if leng < 5:
            lon_step += 0.00001141 * 5 
            lat_step += 0.00000899 * 5
        else:
            break
    return ret


def calculate_the_transition_probability():
    transition_probability = [KAPPA * [0] for i in range(len(nodes))]  # B_ij 
    for idx, node_item in tqdm(enumerate(nodes), desc='Calculating transition probabilities'):
        # if idx > 1: break
        node_lon = node_item[0]
        node_lat = node_item[1]
        ans = get_nodes_in_grid(node_lon, node_lat)
        ans_len = float(len(ans))
        probability = [0 for i in range(KAPPA)]  # B_ij
        for ans_item in ans:
            end_lon = ans_item[5]
            end_lat = ans_item[6]
            in_which_cluster = get_in_which_cluster(end_lon, end_lat)
            probability[in_which_cluster] += 1
        for pro_idx, probability_item in enumerate(probability):
            probability[pro_idx] = float(probability[pro_idx])
            probability[pro_idx] = probability[pro_idx] / ans_len
        for j in range(len(transition_probability[idx])):
            transition_probability[idx][j] = probability[j]

    return transition_probability


def main():
    spatial_sample = [[lon[i], lat[i]] for i in range(len(lon))]
    y_pred = KMeans(n_clusters=KAPPA, random_state=900).fit_predict(spatial_sample)
    with open('init_spatial_cluster_pred.txt', 'w+') as ff:
        for col in y_pred:
            ff.write('%d\n' % col)
    
    for idx, cluster_id in enumerate(y_pred):
        spatial_cluster[cluster_id].append(idx)
    
    for turn in tqdm(range(5), desc='Working...'):
        last = 0
        probs = calculate_the_transition_probability()
        transition_sample = probs
        # print(transition_sample[:3])
        transition_pred = KMeans(n_clusters=K_T, random_state=900).fit_predict(transition_sample)

        for item in transition_cluster:
            item.clear()
        for idx, item in enumerate(transition_pred):
            transition_cluster[item].append(idx)
        tmp_spatial_list = []
        for spatial_cluster_item in spatial_cluster:
            spatial_cluster_item.clear()
        for idx, item in enumerate(transition_cluster):
            print('len(item) = %d\n' % len(item))
            if len(item) == 0: continue
            tmp_spatial_list.clear()
            for k in item:
                tmp_spatial_list.append(k)
            sub_spatial_sample = [[lon[i], lat[i]] for i in tmp_spatial_list]
            # debug
            with open('./run-log-file.txt', 'w+') as log:
                log.write('spatial sample generated by transition cluster %d\n' % idx)
                for Debug in sub_spatial_sample:
                    for Debug_item in Debug:
                        log.write('%f ' % Debug_item)
                    log.write('\n')
            # debug
            n = len(tmp_spatial_list)
            N = len(nodes)
            size = math.floor((n * KAPPA) / N + 1 / 2)
            print('size = %d\n' % size)
            spatial_pred = KMeans(n_clusters=size, random_state=900).fit_predict(sub_spatial_sample)
            spatial_pred = [_item + last for _item in spatial_pred]
            last = max(spatial_pred) + 1

            for index in range(len(tmp_spatial_list)):
                spatial_cluster[spatial_pred[index]].append(tmp_spatial_list[index])
        
        print(spatial_cluster)
        # log
        with open('./run-log-file.txt', 'a') as log_file:
            for j, debug_item in enumerate(spatial_cluster):
                log_file.write('%d :' % j)
                log_file.write('\n')
                for sub_item_ in debug_item:
                    log_file.write('%d ' % sub_item_)
                log_file.write('\n')
            # log_file.close()
        # log

    # result
    with open('./data/spatial-cluster.txt', 'w+') as f:
        for j, spatial_cluster_result_item in enumerate(spatial_cluster):
            f.write('%d :' % j)
            f.write('\n')
            for sub_item in spatial_cluster_result_item:
                f.write('%d ' % sub_item)
            f.write('\n')
        # f.close()
    # result

    cursor.close()
    conn.close()

main()
