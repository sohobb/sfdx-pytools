import sys
import os
import xml.etree.ElementTree as ET
import pandas as pd
from pyvis.network import Network
import utils
config = utils.Config()


def parse_refere_to(file):
    fieldName, fieldType, targetObject = None, None, None

    root = config.get_xml_root(file)

    for child in root:
        if child.tag == "referenceTo":
            targetObject = child.text
        elif child.tag == "fullName":
            fieldName = child.text
        elif child.tag == "type":
            fieldType = child.text

    return fieldName, fieldType, targetObject


def export_csv():
    result = [("object", "field", "type", "target")]
    for path, dirs, files in os.walk("force-app/main/default/objects"):
        if path.endswith("fields"):
            objectName = path.split(os.sep)[-2]
            for file in files:
                relation = parse_refere_to(os.path.join(path, file))
                if relation[-1]:
                    result.append((objectName, *relation))
    with open(config.join_result_path("relationship.csv"), "w") as f:
        f.writelines(map(lambda t: ",".join(t)+"\n", result))


def generate_html(obj: str = None):
    if not os.path.exists(config.join_result_path("relationship.csv")):
        export_csv()
    df = pd.read_csv(config.join_result_path("relationship.csv"))
    if obj:
        df = df[(df["object"] == obj) | (df["target"] == obj)]
    df["source"] = df["object"] + "." + df["field"]
    pyvis_G = Network(directed=True)
    pyvis_G.add_nodes(set(df["source"].tolist()+df["target"].tolist()))
    for _, row in df.iterrows():
        pyvis_G.add_edge(source=row["source"], to=row["target"])
    pyvis_G.show_buttons(filter_=['physics'])
    pyvis_G.toggle_physics(True)
    htmlName = obj if obj else "all-objects"
    pyvis_G.show(config.join_result_path(
        "{}.html".format(htmlName)).replace(config.PROJECT_ROOT_FOLDER, "."))


if __name__ == "__main__":
    if (len(sys.argv) == 2):
        objectName = sys.argv[1]
    else:
        objectName = None
    export_csv()
    generate_html(objectName)
