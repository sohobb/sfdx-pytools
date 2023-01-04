import utils
import sys
import xml.etree.ElementTree as ET
import re


config = utils.Config()


class ActionCall:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.label = element.find("label").text
        self.actionName = element.find("actionName").text
        self.actionType = element.find("actionType").text
        self.connector = None
        if element.find("connector"):
            self.connector = element.find(
                "connector").find("targetReference").text

    def __str__(self) -> str:
        abbr = "({})"
        if (self.actionType == "emailAlert"):
            abbr = abbr.format("M")
        elif self.actionType == "flow":
            abbr = abbr.format("F")

        return "{}【{}】\n{}".format(abbr, self.label, self.actionName)


class Formula:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.expression = element.find("expression").text

    def __str__(self) -> str:
        return "{}".format(self.expression).replace('"', "'")


class Condition:
    def __init__(self, element) -> None:
        self.leftValueReference = element.find(
            "leftValueReference").text.replace("SObject.", "")
        self.operator = element.find("operator").text
        self.rightValue = "null"
        if element.find("rightValue"):
            self.rightValue = element.find("rightValue")[0].text

        if self.operator == "EqualTo":
            self.operator = "=="
        elif self.operator == "IsNull":
            if self.rightValue == "false":
                self.operator = "!="
            elif self.rightValue == "true":
                self.operator = "=="
            self.rightValue = "null"

    def __str__(self) -> str:
        return "{} {} {}".format(self.leftValueReference, self.operator, self.rightValue)


class Rule:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.label = element.find("label").text
        self.conditionLogic = element.find("conditionLogic").text
        self.conditions = [Condition(it) for it in element.findall(
            "conditions")]
        self.connector = element.find("connector")[0].text

    def __str__(self) -> str:
        if (self.conditionLogic in ["and", "or"] and len(self.conditions) > 0):
            return " \n{} ".format(self.conditionLogic).join([str(it) for it in self.conditions])
        else:
            s = self.conditionLogic
            for num in re.findall(r'\b\d+\b', self.conditionLogic):
                condition = self.conditions[(int)(num) - 1]
                s = re.sub(r'\b{}\b'.format(num), str(condition), s)
            return s


class InputAssignment:
    def __init__(self, element) -> None:
        self.field = element.find("field").text
        self.value = element.find("value")[0].text

    def __str__(self) -> str:
        return "{}={}".format(self.field, self.value)


class RecordCreate:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.label = element.find("label").text
        self.object = element.find("object").text
        self.connector = None
        if element.find("connector"):
            self.connector = element.find("connector")[0].text

        self.inputAssignments = [InputAssignment(
            it) for it in element.findall("inputAssignments")]

    def __str__(self) -> str:
        return "(C)【{}】{}\n{}".format(self.label, self.object, "\n".join([str(it) for it in self.inputAssignments]))


class RecordUpdate:
    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.label = element.find("label").text
        self.connector = None
        if element.find("connector"):
            self.connector = element.find("connector")[0].text

        self.filterLogic = element.find("filterLogic").text

        self.inputAssignments = [InputAssignment(
            it) for it in element.findall("inputAssignments")]

    def __str__(self) -> str:
        return "(U)【{}】\n{}".format(self.label, "\n".join([str(it) for it in self.inputAssignments]))


class Decision:

    def __init__(self, element) -> None:
        self.name = element.find("name").text
        self.label = element.find("label").text
        self.defaultConnector = None
        self.rules = [Rule(it) for it in element.findall("rules")]
        if element.find("defaultConnector"):
            self.defaultConnector = element.find(
                "defaultConnector").find("targetReference").text
        self.actions = []

    def __str__(self) -> str:
        s = ""
        for rule in self.rules:
            s += "【{}】\n{}".format(rule.label, rule)
        return s

    def set_actions(self, allActions):
        actionName = self.rules[0].connector

        while actionName in allActions:
            self.actions.append(allActions[actionName])
            actionName = allActions[actionName].connector

    def getActionsString(self):
        return "\n".join([str(it) for it in self.actions])


class Process:
    def __init__(self, name) -> None:
        self.name = name
        path = "force-app/main/default/flows/{}.flow-meta.xml".format(name)
        self.root = config.get_xml_root(path)
        self.decistions = {}
        self.allActions = {}
        self.decistionOrdered = []
        self.formulas = {}
        self.start = ""
        self.label = ""
        self.processMetadataValues = {}
        for item in self.root:
            if item.tag == "actionCalls":
                r = ActionCall(item)
                self.allActions[r.name] = r
            elif item.tag == "decisions":
                r = Decision(item)
                self.decistions[r.name] = r
            elif item.tag == "recordCreates":
                r = RecordCreate(item)
                self.allActions[r.name] = r
            elif item.tag == "recordUpdates":
                r = RecordUpdate(item)
                self.allActions[r.name] = r
            elif item.tag == "formulas":
                r = Formula(item)
                self.formulas[r.name] = r
            elif item.tag == "label":
                self.label = item.text
            elif item.tag == "startElementReference":
                self.start = item.text
            elif item.tag == "processMetadataValues":
                key = item[0].text
                value = item[1][0].text
                self.processMetadataValues[key] = value
            elif item.tag == "processType":
                key = "processType"
                value = item.text
                self.processMetadataValues[key] = value
            elif item.tag == "status":
                self.active = item.text == "Active"

        node = self.decistions[self.start]
        while node:
            if (node.name != "sobjectInputCheckDecision"):
                self.decistionOrdered.append(node)
            if (node.defaultConnector in self.decistions):
                node = self.decistions[node.defaultConnector]
            elif (node.rules[0].connector in self.decistions):
                node = self.decistions[node.rules[0].connector]
            else:
                node = None

    def to_csv(self):
        with open(config.join_result_path("{}.flow-meta.csv".format(self.name)), "w") as f:
            s = "Process Name,API Name,Active,Timing,Condition,Action\n"
            timing = self.processMetadataValues["TriggerType"] if "TriggerType" in self.processMetadataValues else self.processMetadataValues["processType"]
            if timing == "onAllChanges":
                timing = "after insert | after update"
            for decision in self.decistionOrdered:
                decision.set_actions(self.allActions)
                s += '"{}","{}","{}","{}","{}","{}"\n'.format(self.label, self.name, self.active, timing,
                                                              str(decision), decision.getActionsString())
            for fml in self.formulas:
                s = re.sub(r'\b{}\b'.format(fml),
                           "({})".format(str(self.formulas[fml])), s)
            f.write(s)


if __name__ == "__main__":
    if (len(sys.argv) == 2):
        processName = sys.argv[1]
    else:
        processName = "case_finish"
    p = Process(processName)
    p.to_csv()
