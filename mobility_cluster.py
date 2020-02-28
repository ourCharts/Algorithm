import pymysql
import numpy as np
import math


db = pymysql.connect(host='localhost', user='root', port=3308,
                       passwd='', db='tenman', charset='utf8')
cursor = db.cursor(pymysql.cursors.SSCursor)

#----------------------------------------全局变量----------------------------------------
taxi_mobility_vector = []
request_mobility_vector = []
mobility_cluster = []
general_mobility_vector = []


alpha = 0.999999921837146  #判断vector夹角的judgement变量





#----------------------------------------算余弦相似度----------------------------------------
def cosine(x,y): 
    sum_xy = 0.0
    normX = 0.0
    normY = 0.0
    for a,b in zip(x,y):
        sum_xy += a*b
        normX += a**2
        normY += b**2
    if normX == 0.0 or normY == 0.0:
        return None
    else:
        tmp = sum_xy / ((normX*normY)**0.5) 
        if tmp<0:
            return -tmp
        return tmp

#-------------------获取订单--------------------
def get_an_order(idx):
    sql = 'SELECT start_longitude, start_latitude, end_longitude, end_latitude FROM myorder LIMIT %d, 1' % (
        idx - 1)
    cursor.execute(sql)
    ret = cursor.fetchall()
    return ret[0]

#-------------------order加入，将加入或新建cluster--------------------
def get_in(order):
    flag = False #flag判断是否有可归属的cluster，若False则新建一个cluster
    min_cos = 2
    min_idx = 0
    for idx,item in enumerate(general_mobility_vector):
        vec1 = (lng1, lat1, lng2, lat2) = order[0:4]
        cos = cosine(vec1,item)
        if cos >= alpha and cos <= min_cos:#判断条件: 在所有cluster中，选取与该其的general vector夹角最小的cluster 
            flag = True
            min_cos = cos
            min_idx = idx
    print(flag)
    if not flag:#新建cluster和对应general vector
        mobility_cluster.append([order])
        general_mobility_vector.append(order)
        return
    else:#加入对应cluster和更新对应general vector
        mobility_cluster[min_idx].append(order)
        a=b=c=d=0
        length = len(mobility_cluster[min_idx])
        for it in range(length):
            a += mobility_cluster[min_idx][it][0]
            b += mobility_cluster[min_idx][it][1]
            c += mobility_cluster[min_idx][it][2]
            d += mobility_cluster[min_idx][it][3]
        general_mobility_vector[min_idx] = (a/length,b/length,c/length,d/length)




def initialize(order_num):#加入num个订单，输出mobility cluster 和general vector
    for i in range(order_num):
        order = get_an_order(i+1)
        get_in(order)
    print(mobility_cluster)
    print(general_mobility_vector)


#=========================执行部分===========================================
initialize(10)
cursor.close()
db.close()
