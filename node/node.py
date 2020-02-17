class node():
    def __init__(self, node_id, lon, lat, cluster_id_belong_to, anchor_node_belong_to):
        self.id = node_id
        self.lon = lon
        self.lat = lat
        self.cluster_id_belong_to = cluster_id_belong_to
        self.anchor_node_belong_to = anchor_node_belong_to