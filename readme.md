### 环境配置

所需要用到的包已包含在虚拟环境中，打开项目目录后，运行目录venv/Scripts中的Activate.ps1即可激活虚拟环境（该文件用于在powershell中激活虚拟环境）

### 数据解释

node-list.csv：包含osm地图上的所有路口点。共有四个字段，其含义分别为：

* lsh_id：表示的是一个点在所有点组成的序列中所占的下标。因为该文件是采用一行一个点的格式来存储的，所以也可以理解为行号
* read_id：表示的是一个点在osm地图上的id
* lat：表示的是一个点的纬度
* lon：表示的是一个点的经度

### 代码解释

#### 函数

在main.py中，包含的函数以及其具体含义分别为：

* get_an_order(idx) 

  从数据库中读取第idx行的记录，这里读取的是myorder表

* rad(deg)

  用于将角度转化为弧度

* get_distance(lon1, lat1, lon2, lat2)

  计算两个经纬点之间的距离，单位是米

* process_out_of_range(pos)

  处理下标，处理超出list范围的情况

* get_closest_node(lon, lat)

  对于经纬度为(lon, lat)的点![](http://latex.codecogs.com/gif.latex?\\mathbf{p})，
  计算osm地图上距离该点最近的点的id。具体计算方法为，将点![](http://latex.codecogs.com/gif.latex?\\mathbf{p})纳入一个“网格”中，然后在网格中查找距离其最近的点。网格与网格内的点的计算方法为，通过预先设定的网格大小，计算出上、下、左、右四个边界，然后通过二分查找确定网格内有哪些点。注意，若当前网格内点的数目小于2，则需要扩大网格的规模。

* get_in_which_cluster(lon, lat):

  计算某个经纬点位于哪一个cluster中(该经纬点来自于数据库中的记录)

* get_nodes_in_grid(lon, lat)

  对于osm上的某个点，在一个网格内搜索与其邻近的历史出发点

* calculate_the_transition_probability()

  计算出每个点的transition probability向量

* main()

  主要运行部分。其中包含部分打印日志的代码，方便debug

#### 重要变量/参数

spatial_cluster：一个200行的二维list，对于第![](http://latex.codecogs.com/gif.latex?\\mathbf{i})行，其中存放的是属于编号为$i$的空间聚类的点的lsh_id

transition_cluster：一个200行的二维list，对于第![](http://latex.codecogs.com/gif.latex?\\mathbf{i})行，其中存放的是属于编号为![](http://latex.codecogs.com/gif.latex?\\mathbf{i})的转移概率聚类的点的lsh_id

KAPPA：在做空间聚类划分时，将所有点划分成KAPPA个聚类

K_T：在做转移概率聚类划分时，将所有点划分成K_T个聚类

NODES_NUM_IN_TRANSITION_CALCULATION：计算一个道路点的transition probability时用到的邻近点的数目

ITERATION_TIME：迭代次数