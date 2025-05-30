import argparse
from pyvis.network import Network
import networkx as nx
import webbrowser
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, session
import os
import tempfile
from datetime import datetime
import shutil
import uuid




""" parser = argparse.ArgumentParser(description="Visualize network topology from Excel.")
parser.add_argument("--font-size", type=int, default=18, help="Font size for node labels")
parser.add_argument("--excel", type=str, default="text_sheet.xlsx", help="Path to the Excel file")
parser.add_argument("--size-user", type=int, default=20, help="Size of user nodes")
parser.add_argument("--size-router", type=int, default=20, help="Size of router nodes")
parser.add_argument("--size-switch", type=int, default=20, help="Size of switch nodes")
parser.add_argument("--size-server", type=int, default=20, help="Size of server nodes")
args = parser.parse_args()

use_naprave = pd.read_excel(args.excel, sheet_name=None) """

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session to work

edge_type_colors = {
    ("U", "U"): "blue",
    ("U", "R"): "orange",
    ("U", "S"): "blue",
    ("U", "SR"): "purple",

    ("R", "U"): "orange",
    ("R", "R"): "red",
    ("R", "S"): "red",
    ("R", "SR"): "brown",

    ("S", "U"): "blue",
    ("S", "R"): "red",
    ("S", "S"): "green",
    ("S", "SR"): "green",

    ("SR", "U"): "purple",
    ("SR", "R"): "brown",
    ("SR", "S"): "green",
    ("SR", "SR"): "black",
}



@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/isolation", methods=['POST'])
def isolation():
    file = request.files["excel"]
    if not file:
        return "No file uploaded", 400
    filename = os.path.splitext(file.filename)[0]

    if os.path.isdir(filename):
        shutil.rmtree(filename)
    UPLOAD_DIR = os.path.join(os.getcwd(), filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
    excel_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{datetime.today().strftime('%Y-%m-%d')}_{file.filename}")

    file.save(excel_path)
    session["excel_path"] = excel_path
    session["font_size"] = int(request.form.get("font_size", 18))
    session["size_user"] = int(request.form.get("size_user", 20))
    session["size_router"] = int(request.form.get("size_router", 20))
    session["size_switch"] = int(request.form.get("size_switch", 20))
    session["size_server"] = int(request.form.get("size_server", 20))
    session["theme"] = request.form.get("theme", "dark")

    # Extract device names from the Excel file
    use_naprave = pd.read_excel(excel_path, sheet_name=None)
    device_names = [sheet_name.strip() for sheet_name in use_naprave.keys()]

    return render_template("isolation.html", device_names=device_names)

@app.route("/upload", methods=["POST"])
def show_network():
    excel_path = session.get("excel_path")
    font_size = session.get("font_size", 18)
    size_user = session.get("size_user", 20)
    size_router = session.get("size_router", 20)
    size_switch = session.get("size_switch", 20)
    size_server = session.get("size_server", 20)
    device_isolate = str(request.form.get("device_isolate", ""))
    theme = request.form.get("theme", session.get("theme", "dark"))

    # ...rest of your code...

    if theme == "light":
        bgcolor = "#fff"
        font_color = "black"
    else:
        bgcolor = "#000"  # Completely black background for dark mode
        font_color = "white"

    use_naprave = pd.read_excel(excel_path, sheet_name=None)
    
    slovar = dict()
    for sheet_name, df in use_naprave.items():
        sheet_name = sheet_name.strip()
        df = df.dropna(how='all')
        tempdict = {}
        for _, row in df.iterrows():
            port = str(row["Port"]).strip()
            ip = str(row.get("IP","")).strip()
            connected_to = str(row["Conected_to"]).strip()
            if pd.notna(connected_to) and connected_to.lower() != "nan":
                tempdict[port] = connected_to
            if str(row["Type"]).lower() != "nan":
                tempdict['Type'] = str(row['Type']).strip()
            if ip:
                tempdict["IP"] = ip
        slovar[sheet_name] = tempdict

    print("Devices in network:", list(slovar.keys()))
    for device, ports in slovar.items():
        for port, connected_device in ports.items():
            if port != "Type":
                print(f"{device} ({port}) -> {connected_device}")

    G = nx.MultiDiGraph()
    edges_added = set()
    if device_isolate == "":

        for device, ports in slovar.items():
            for port, connected_device in ports.items():
                if port == "Type" or connected_device not in slovar:
                    continue
                key_out = (device, connected_device, port)
                if key_out not in edges_added:
                    type1 = slovar.get(device, {}).get("Type", "")
                    type2 = slovar.get(connected_device, {}).get("Type", "")
                    edge_color = edge_type_colors.get((type1, type2), "gray")
                    G.add_edge(device, connected_device, label=port, color=edge_color)
                    edges_added.add(key_out)
                for other_port, target in slovar[connected_device].items():
                    if other_port == "Type":
                        continue
                    if target == device:
                        key_in = (connected_device, device, other_port)
                        if key_in not in edges_added:
                            type1 = slovar.get(connected_device, {}).get("Type", "")
                            type2 = slovar.get(device, {}).get("Type", "")
                            edge_color = edge_type_colors.get((type1, type2), "gray")
                            G.add_edge(connected_device, device, label=other_port, color=edge_color)
                            edges_added.add(key_in)
                        break

        net = Network(height="750px", width="100%", bgcolor=bgcolor, font_color=font_color, directed=True)
        net.force_atlas_2based(gravity=-50, central_gravity=0.005, spring_length=150, damping=0.8)
        net.from_nx(G)

        # When updating node font color:
        for i, node in enumerate(net.nodes):
            node_id = node["id"]
            node_type = slovar.get(node_id, {}).get("Type", "")
            ip = slovar.get(node_id, {}).get("IP", "")
            net.nodes[i]["font"] = {"size": font_size, "color": font_color}
            tooltip = f"Device: {node_id}\nIP:{ip}"

            if node_type == "U":
                size = size_user
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_computer.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color},
                    "title": tooltip
                })
            elif node_type == "R":
                size = size_router
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_router.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })
            elif node_type == "S":
                size = size_switch
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_switch.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })
            elif node_type == "SR":
                size = size_server
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/server.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })

        # Set edge label font color for visibility and add outline for readability
        edge_stroke_color = "#fff" if font_color == "black" else "#000"
        for edge in net.edges:
            edge["font"] = {
                "color": font_color,
                "strokeWidth": 4,
                "strokeColor": edge_stroke_color
            }

        filename = "graph.html"
        unique_filename = f"network_{uuid.uuid4().hex}.html"
        file_path = os.path.join("static", "graphs", unique_filename)
        net.save_graph(file_path)
        return send_file(file_path)

    else:
        i = 1
        vsi_connected_devici = []
        print("NEKI JE U DEVICE NAMU")
        print(device_isolate)
        print(slovar[device_isolate])
        for key, value in slovar[device_isolate].items():
            if key != "Type":
                type1 = slovar.get(device_isolate, {}).get("Type", "")
                type2 = slovar.get(value, {}).get("Type", "")
                edge_color = edge_type_colors.get((type1, type2), "gray")
                G.add_edge(device_isolate, value, label=key, color=edge_color)
                i += 1
            else:
                pass
        for key, value in slovar[device_isolate].items():
            if key != "Type":
                if value not in vsi_connected_devici:
                    vsi_connected_devici.append(value)

        print(vsi_connected_devici)
        for device in vsi_connected_devici:
            for key, value in slovar[device].items():
                if value == device_isolate:
                    type1 = slovar.get(device, {}).get("Type", "")
                    type2 = slovar.get(device_isolate, {}).get("Type", "")
                    edge_color = edge_type_colors.get((type1, type2), "gray")
                    G.add_edge(device, device_isolate, label=key, color=edge_color)

    

    net = Network(height="750px", width="100%", bgcolor=bgcolor, font_color=font_color, directed=True)
    net.force_atlas_2based(gravity=-50, central_gravity=0.005, spring_length=150, damping=0.8)
    net.from_nx(G)

    for i, node in enumerate(net.nodes):
            node_id = node["id"]
            node_type = slovar.get(node_id, {}).get("Type", "")
            ip = slovar.get(node_id, {}).get("IP", "")
            net.nodes[i]["font"] = {"size": font_size, "color": font_color}
            tooltip = f"Device: {node_id}\nIP:{ip}"

            if node_type == "U":
                size = size_user
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_computer.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color},
                    "title": tooltip
                })
            elif node_type == "R":
                size = size_router
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_router.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })
            elif node_type == "S":
                size = size_switch
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/cisco_switch.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })
            elif node_type == "SR":
                size = size_server
                net.nodes[i].update({
                    "shape": "image",
                    "image": "static/Imgs/server.png",
                    "label": node_id,
                    "shapeProperties": {"useImageSize": False},
                    "size": size,
                    "font": {"size": int(size * 0.6), "color": font_color}
                })
            edge_stroke_color = "#fff" if font_color == "black" else "#000"
            for edge in net.edges:
                edge["font"] = {
                    "color": font_color,
                    "strokeWidth": 4,
                    "strokeColor": edge_stroke_color
                }

    filename = "graph.html"
    unique_filename = f"network_{uuid.uuid4().hex}.html"
    file_path = os.path.join("static", "graphs", unique_filename)
    net.save_graph(file_path)
    return send_file(file_path)


if __name__ == "__main__":
    app.run(debug=True)
