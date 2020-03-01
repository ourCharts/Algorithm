import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv('C:/Users/Administrator/Desktop/tuesnight/Algorithm/data/node-list.csv')
lon = df.loc[:, 'lon']
lat = df.loc[:, 'lat']
color = [0] * 7669

with open('C:/Users/Administrator/Desktop/tuesnight/Algorithm/data/spatial-cluster.txt', 'r') as file:
    pointer = 0
    while True:
        line = file.readline()
        if not line:
            break
        if ':' in line or line == '':
            pointer = int(line.split()[0])
            continue
        processed_line = []
        lineli = line.split(' ')
        for item in lineli:
            if item != '\n' and item != '\r' and item != ' ':
                processed_line.append(int(item))
        for node in processed_line:
            color[node] = pointer

init_color = []
print(color)
with open('C:/Users/Administrator/Desktop/tuesnight/Algorithm/data/init_spatial_cluster_pred.txt', 'r') as ff:
	while True:
		line  = ff.readline()
		if not line:
			break
		line.strip()
		init_color.append(int(line))

print(init_color)
plt.figure(figsize=(12.8, 7.2))
plt.subplot(1, 2, 1)
plt.scatter(lon, lat, c=color, s=1)
plt.subplot(1, 2, 2)
plt.scatter(lon, lat, c=init_color, s=1)
plt.show()
