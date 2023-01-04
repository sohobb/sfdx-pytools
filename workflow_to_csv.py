import sys
import xml.etree.ElementTree as ET
import re
import utils
STRANGE_MAP = {
    "%28": "(",
    "%29": ")",
    "%EF%BC%88": "（",
    "%EF%BC%89": "）",
    "%21": "!",
    "%3A": ":",
    "%2F": "/"
}
config = utils.Config()


class Alert:
    def __init__(self, element) -> None:
        self.fullName = element.find("fullName").text
        self.description = element.find("description").text

    def __str__(self) -> str:
        return "(M)【{}】\n{}".format(self.description, self.fullName)


class FieldUpdate:
    def __init__(self, element) -> None:
        self.fullName = element.find("fullName").text
        self.name = element.find("name").text
        self.field = element.find("field").text
        self.operation = element.find("operation").text
        self.value = None
        if self.operation == "LookupValue":
            self.value = element.find("lookupValue").text
        elif self.operation == "Literal":
            self.value = element.find("literalValue").text
        elif self.operation == "Formula":
            self.value = element.find(
                "formula").text.replace('"', "'")

    def __str__(self) -> str:
        return "(U)【{}】\n{}={}".format(self.name, self.field, self.value)


class Action:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.type = element.find("type").text


class CriteriaItem:
    def __init__(self, element) -> None:
        self.field = element.find("field").text
        self.operation = element.find("operation").text
        if self.operation == "equals":
            self.operation = "=="
        elif self.operation == "notEqual":
            self.operation = "!="
        self.value = "null"
        if element.find("value") != None:
            self.value = element.find("value").text

    def __str__(self) -> str:
        return "{} {} {}".format(self.field, self.operation, self.value)


class Rule:
    def __init__(self, element) -> None:
        self.fullName = element.find("fullName").text
        self.triggerType = element.find("triggerType").text
        if self.triggerType == "onCreateOnly":
            self.triggerType = "after insert"
        elif self.triggerType == "onCreateOrTriggeringUpdate":
            self.triggerType = "after insert, after update"
        elif self.triggerType == "onAllChanges":
            self.triggerType = "after insert, after update"
        self.active = element.find("active").text == "true"
        self.booleanFilter = None
        if element.find("booleanFilter") != None:
            self.booleanFilter = element.find("booleanFilter").text
        self.criteriaItems = [CriteriaItem(
            it) for it in element.findall("criteriaItems")]
        self.actions = [Action(it)
                        for it in element.findall("actions")]
        self.actionsOrigin = []

    def setActions(self, actions):
        for a in self.actions:
            self.actionsOrigin.append(actions[a.name])

    def getJoinedCriteria(self) -> str:
        if (self.booleanFilter):
            s = self.booleanFilter
            for num in re.findall(r'\b\d+\b', self.booleanFilter):
                condition = self.criteriaItems[(int)(num) - 1]
                s = re.sub(r'\b{}\b'.format(num), str(condition), s)
            return s
        else:
            return " and ".join([str(it) for it in self.criteriaItems])

    def __str__(self) -> str:
        return '"{}","{}","{}","{}","{}"'.format(
            self.fullName,
            self.triggerType,
            self.active,
            self.getJoinedCriteria(),
            "\n".join([str(it)for it in self.actionsOrigin])
        )


class Workflow:
    def __init__(self, path) -> None:
        self.object = re.split(r'\.|/', path)[-3]
        self.root = config.get_xml_root(path)
        self.actions = {}
        self.rules = []

        for element in self.root:
            if element.tag == "alerts":
                e = Alert(element)
                self.actions[e.fullName] = e
            elif element.tag == "fieldUpdates":
                e = FieldUpdate(element)
                self.actions[e.fullName] = e
            elif element.tag == "rules":
                e = Rule(element)
                e.setActions(self.actions)
                self.rules.append(e)

    def to_csv(self) -> str:
        s = "Rule,Timing,Active,Condition,Action\n"
        for rule in self.rules:
            s = s + "{}\n".format(str(rule))
        for key in STRANGE_MAP:
            s = s.replace(key, STRANGE_MAP[key])
        with open(config.join_result_path("{}.workflow-meta.csv".format(self.object)), "w") as f:
            f.write(s)


def convert_to_xml(processName: str):
    p = Workflow(
        "force-app/main/default/workflows/{}.workflow-meta.xml".format(processName))
    p.to_csv()


if __name__ == "__main__":
    if (len(sys.argv) == 2):
        processName = sys.argv[1]
    else:
        processName = "Case"
    convert_to_xml(processName)
