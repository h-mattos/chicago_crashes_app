import polars as pl
import flet as ft
from PIL import Image, ImageDraw
import requests
import json
from io import BytesIO
import base64
import numpy as np
from scipy.sparse.csgraph import shortest_path, connected_components
from scipy.sparse import csr_matrix
from catboost import CatBoostClassifier
import matplotlib.cm as cm
from matplotlib.colors import rgb2hex, Normalize
from datetime import datetime
from time import sleep
import os

W, H = int(1290 / 4), int(2796 / 4)
BG_COLOR = "#f5f3f3"
LINE_COLOR = "#cfd3da"
ROUTE_COLOR = "#598be3"
LATLON_AR = 1.0 / np.cos(41.837890012090874 * np.pi / 180)  # LATLON_AR = LAT/LON
SCREEN_AR = H / W
BBOX_PAD_PCT = 0.05
# MAP_FILE = f"{os.path.abspath(os.curdir)}/map.png"
# MODEL_FILE = f"{os.path.abspath(os.curdir)}/minimod.cbm"
# NET_FILE = f"{os.path.abspath(os.curdir)}/Data/chicago-net.parquet"
# NODES_FILE = f"{os.path.abspath(os.curdir)}/Data/illinois-nodes.parquet"
# EDGES_FILE = f"{os.path.abspath(os.curdir)}/Data/illinois-edges.parquet"
MAP_FILE = "./map.png"
MODEL_FILE = "./minimod.cbm"
NET_FILE = "./Data/chicago-net.parquet"
# NODES_FILE = "./Data/illinois-nodes.parquet"
# EDGES_FILE = "./Data/illinois-edges.parquet"
NODES_FILE = "./Data/nodes.parquet"
EDGES_FILE = "./Data/edges.parquet"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
}

model = CatBoostClassifier()
model.load_model(MODEL_FILE)
net_data = pl.read_parquet(NET_FILE)
# nodes = pl.read_parquet(NODES_FILE)
# nodes = nodes.filter(
#     pl.col("lat")
#     .is_between(
#         min(net_data["lat1"].min(), net_data["lat2"].min()),
#         max(net_data["lat1"].max(), net_data["lat2"].max()),
#     )
#     .and_(
#         pl.col("lon").is_between(
#             min(net_data["lon1"].min(), net_data["lon2"].min()),
#             max(net_data["lon1"].max(), net_data["lon2"].max()),
#         )
#     )
# )
# nodes = nodes.with_row_index()
# edges = pl.read_parquet(EDGES_FILE)
# edges = edges.filter(pl.col("node_id").is_in(nodes["node_id"]))
# edges = (
#     edges.select(
#         [
#             pl.col("way_id"),
#             pl.col("way_id").shift(-1).alias("way_id2"),
#             pl.col("node_id").alias("node_id1"),
#             pl.col("node_id").shift(-1).alias("node_id2"),
#         ]
#     )
#     .filter(pl.col("way_id").eq(pl.col("way_id2")))
#     .drop("way_id2")
# )
# edges = edges.with_row_index("group")
# edges = edges.unique()
# edges = edges.join(
#     nodes.rename({"index": "index1", "lat": "lat1", "lon": "lon1"}),
#     left_on="node_id1",
#     right_on="node_id",
#     how="left",
# ).join(
#     nodes.rename({"index": "index2", "lat": "lat2", "lon": "lon2"}),
#     left_on="node_id2",
#     right_on="node_id",
#     how="left",
# )
# edges = edges.with_columns(
#     [
#         pl.col("lat1")
#         .sub(pl.col("lat2"))
#         .mul(LATLON_AR)
#         .pow(2)
#         .add(pl.col("lon1").sub(pl.col("lon2")).pow(2))
#         .sqrt()
#         .alias("dist")
#     ]
# )
# csr_graph = csr_matrix(
#     (edges["dist"].to_numpy(), (edges["index1"].to_numpy(), edges["index2"].to_numpy()))
# )
# n_components, labels = connected_components(csr_graph, directed=False)
# max_lab, counts = np.unique(labels, return_counts=True)
# max_lab = max_lab[np.argmax(counts)]
# edges = edges.filter(
#     pl.col("index1")
#     .is_in(np.argwhere(labels == max_lab).flatten())
#     .and_(pl.col("index2").is_in(np.argwhere(labels == max_lab).flatten()))
# )
# nodes = nodes.filter(pl.col("index").is_in(np.argwhere(labels == max_lab).flatten()))
# edges.columns
# edges.select(['index1', 'index2', 'dist']).write_parquet(EDGES_FILE, compression='zstd', compression_level=22)
# nodes.write_parquet(NODES_FILE, compression='zstd', compression_level=22)

edges = pl.read_parquet(EDGES_FILE)
nodes = pl.read_parquet(NODES_FILE)

csr_graph = csr_matrix(
    (edges["dist"].to_numpy(), (edges["index1"].to_numpy(), edges["index2"].to_numpy()))
)


def compute_route(lat1, lon1, lat2, lon2):
    idx1 = nodes.with_columns(
        [
            pl.col("lat")
            .sub(pl.lit(lat1))
            .mul(LATLON_AR)
            .pow(2)
            .add(pl.col("lon").sub(pl.lit(lon1)).pow(2))
            .sqrt()
            .alias("dist")
        ]
    ).select([pl.col("index").get(pl.col("dist").arg_min())])[0, 0]
    idx2 = nodes.with_columns(
        [
            pl.col("lat")
            .sub(pl.lit(lat2))
            .mul(LATLON_AR)
            .pow(2)
            .add(pl.col("lon").sub(pl.lit(lon2)).pow(2))
            .sqrt()
            .alias("dist")
        ]
    ).select([pl.col("index").get(pl.col("dist").arg_min())])[0, 0]
    _, predecessors = shortest_path(
        csr_graph, directed=False, indices=idx1, return_predecessors=True
    )
    route = [idx2]
    while predecessors[route[-1]] != -9999:
        route.append(predecessors[route[-1]])
    return route


# 'Wilbur Wright College, Chicago'
# 'Riis Park, Chicago'
# '6428 W Roscoe St, Chicago'
# 'The Spice Room, 2906 W Armitage Ave, Chicago'
# 'National Museum of Mexican Art, Chicago'
# orig = 'Wilbur Wright College, Chicago'

def main(page: ft.Page):
    page.window_width = W
    page.window_height = H
    page.padding = 0

    def draw_map(orig, dest):
        orig = requests.get(
            f'https://nominatim.openstreetmap.org/search.php?q="{orig}"&format=jsonv2',
            headers=HEADERS
        )
        sleep(2)
        dest = requests.get(
            f'https://nominatim.openstreetmap.org/search.php?q="{dest}"&format=jsonv2',
            headers=HEADERS
        )
        if ('Access blocked' in orig.content.decode()) or ('Access blocked' in dest.content.decode()):
            raise ValueError('Access blocked by OSM Nominatim.')
        orig_info = json.loads(orig.content.decode())[0]
        dest_info = json.loads(dest.content.decode())[0]
        lat1 = float(orig_info["lat"])
        lon1 = float(orig_info["lon"])
        lat2 = float(dest_info["lat"])
        lon2 = float(dest_info["lon"])
        bbox_lats = sorted([float(orig_info["lat"]), float(dest_info["lat"])])
        bbox_lons = sorted([float(orig_info["lon"]), float(dest_info["lon"])])
        bbox_lats = [
            bbox_lats[0] - BBOX_PAD_PCT * (bbox_lats[1] - bbox_lats[0]),
            bbox_lats[1] + BBOX_PAD_PCT * (bbox_lats[1] - bbox_lats[0]),
        ]
        bbox_lons = [
            bbox_lons[0] - BBOX_PAD_PCT * (bbox_lons[1] - bbox_lons[0]),
            bbox_lons[1] + BBOX_PAD_PCT * (bbox_lons[1] - bbox_lons[0]),
        ]

        def process_bbox(bbox_lats, bbox_lons):
            if (
                LATLON_AR
                * (bbox_lats[1] - bbox_lats[0])
                / (bbox_lons[1] - bbox_lons[0])
                < SCREEN_AR
            ):
                bbox_lats = [
                    (bbox_lats[0] + bbox_lats[1]) / 2
                    - ((bbox_lons[1] - bbox_lons[0]) / (2 * LATLON_AR * W)) * H,
                    (bbox_lats[0] + bbox_lats[1]) / 2
                    + ((bbox_lons[1] - bbox_lons[0]) / (2 * LATLON_AR * W)) * H,
                ]
            else:
                bbox_lons = [
                    (bbox_lons[0] + bbox_lons[1]) / 2
                    - ((bbox_lats[1] - bbox_lats[0]) * LATLON_AR / (2 * H)) * W,
                    (bbox_lons[0] + bbox_lons[1]) / 2
                    + ((bbox_lats[1] - bbox_lats[0]) * LATLON_AR / (2 * H)) * W,
                ]

            def lat2screen(lat):
                return H - max(
                    min((lat - bbox_lats[0]) * H / (bbox_lats[1] - bbox_lats[0]), H), 0
                )

            def lon2screen(lon):
                return max(
                    min((lon - bbox_lons[0]) * W / (bbox_lons[1] - bbox_lons[0]), W), 0
                )

            return bbox_lats, bbox_lons, lat2screen, lon2screen

        bbox_lats, bbox_lons, lat2screen, lon2screen = process_bbox(
            bbox_lats, bbox_lons
        )
        draw_data = net_data.filter(
            pl.col("lat1")
            .is_between(*bbox_lats)
            .or_(pl.col("lat2").is_between(*bbox_lats))
            .and_(
                pl.col("lon1")
                .is_between(*bbox_lons)
                .or_(pl.col("lon2").is_between(*bbox_lons))
            )
        )
        img = Image.new("RGB", (W, H), color=BG_COLOR)
        img_d = ImageDraw.Draw(img)
        for shape in zip(
            draw_data["lon1"], draw_data["lat1"], draw_data["lon2"], draw_data["lat2"]
        ):
            img_d.line(
                [
                    (lon2screen(shape[0]), lat2screen(shape[1])),
                    (lon2screen(shape[2]), lat2screen(shape[3])),
                ],
                fill=LINE_COLOR,
                width=1,
            )
        route = compute_route(lat1, lon1, lat2, lon2)
        if timePicker.value is not None:
            time_val = timePicker.value
        else:
            time_val = datetime.now()
        for i, j in zip(route[:-1], route[1:]):
            node1 = nodes.filter(pl.col("index").eq(i))
            node2 = nodes.filter(pl.col("index").eq(j))
            shape = (node1["lon"][0], node1["lat"][0], node2["lon"][0], node2["lat"][0])
            img_d.line(
                [
                    (lon2screen(shape[0]), lat2screen(shape[1])),
                    (lon2screen(shape[2]), lat2screen(shape[3])),
                ],
                fill=prob2col(
                    model.predict_proba(
                        [
                            time_val.hour,
                            time_val.weekday() + 1,
                            node1["lat"][0],
                            node1["lon"][0],
                        ]
                    )[1]
                ),
                width=2,
            )
        img.save(MAP_FILE)

    norm = Normalize(0.1, 0.3)

    def prob2col(p) -> str:
        p = norm(p)
        return rgb2hex(cm.autumn(int(p * 255)))

    def set_time(data):
        timePicker.value = data

    bg_img = ft.Image(
        src=MAP_FILE,
        width=W,
        height=H,
        fit=ft.ImageFit.FILL,
    )

    def update_bg():
        img = Image.open(MAP_FILE)
        buff = BytesIO()
        img.save(buff, format="JPEG")
        new_image_string = base64.b64encode(buff.getvalue()).decode("utf-8")
        bg_img.src_base64 = new_image_string

    def tf1_submit(e):
        tf2.focus()

    def tf2_submit(e):
        tf1.focus()

    tf1 = ft.TextField(
        label="Starting Location",
        bgcolor="#99000000",
        text_style=ft.TextStyle(color="#FFFFFF"),
        label_style=ft.TextStyle(color="#F9F9F9"),
        # focused_color="#000000",
        on_submit=tf1_submit,
    )
    tf2 = ft.TextField(
        label="Destination",
        bgcolor="#99000000",
        text_style=ft.TextStyle(color="#FFFFFF"),
        label_style=ft.TextStyle(color="#F9F9F9"),
        # focused_color="#000000",
        on_submit=tf2_submit,
    )
    timePicker = ft.CupertinoDatePicker(
        on_change=lambda e: set_time(e.data),
        date_picker_mode=ft.CupertinoDatePickerMode.DATE_AND_TIME,
    )
    date_button = ft.FilledTonalButton(
        "Pick date",
        icon=ft.icons.CALENDAR_MONTH,
        on_click=lambda e: page.show_bottom_sheet(
            ft.CupertinoBottomSheet(
                timePicker,
                height=216,
                padding=ft.padding.only(top=6),
            )
        ),
    )

    def update_img(e):
        draw_map(tf1.value, tf2.value)
        update_bg()
        bg_img.update()
        page.update()

    run_button = ft.ElevatedButton(
        "Go", icon=ft.icons.RUN_CIRCLE_OUTLINED, on_click=update_img
    )

    st = ft.Stack(
        [
            bg_img,
            ft.Container(
                ft.Column(
                    [tf1, tf2, ft.Row([date_button, run_button])],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=10,
            ),
        ]
    )
    page.add(st)


ft.app(target=main)
