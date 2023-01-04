import os
import xml.etree.ElementTree as ET


class Config:
    def __init__(self):
        if os.getcwd().split(os.sep)[-1] == "sfdx-pytools":
            os.chdir("../")
        self.PROJECT_ROOT_FOLDER = os.getcwd()
        self.RESULT_FOLDER = os.path.join(
            self.PROJECT_ROOT_FOLDER, "sfdx-pytools/result")
        self.NAME_SPACE = "http://soap.sforce.com/2006/04/metadata"

        if not os.path.exists(self.RESULT_FOLDER) or os.path.isfile(self.RESULT_FOLDER):
            os.makedirs(self.RESULT_FOLDER)

    def join_result_path(self, file: str) -> str:
        return os.path.join(self.RESULT_FOLDER, file)

    def get_xml_root(self, path: str):
        f = open(path, "r", errors="ignore")
        xml_str = f.read()
        xml_str = xml_str.replace(self.NAME_SPACE, "")
        return ET.fromstring(xml_str)


if __name__ == "__main__":
    c = Config()
