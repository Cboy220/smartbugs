from sarif_om import *

from src.output_parser.Parser import Parser
from src.output_parser.SarifHolder import parseRuleIdFromMessage, parseLevel, parseMessage, parseUri, \
    isNotDuplicateRule, isNotDuplicateArtifact


class Osiris(Parser):
    def __init__(self):
        pass

    def extract_result_line(self, line):
        line = line.replace("INFO:symExec:	  ", '')
        index_split = line.index(":")
        key = line[:index_split].lower().replace(' ', '_').replace('(', '').replace(')', '').replace('└>_', '').strip()
        value = line[index_split + 1:].strip()
        if "True" == value:
            value = True
        elif "False" == value:
            value = False
        return (key, value)

    def parse(self, str_output):
        output = []
        current_contract = None
        current_error = None
        lines = str_output.splitlines()
        for line in lines:
            if "INFO:root:Contract" in line:
                if current_contract is not None:
                    output.append(current_contract)
                current_contract = {
                    'errors': []
                }
                (file, contract_name, _) = line.replace("INFO:root:Contract ", '').split(':')
                current_contract['file'] = file
                current_contract['name'] = contract_name
            elif "INFO:symExec:	  " in line and '---' not in line and '======' not in line:
                current_error = None
                (key, value) = self.extract_result_line(line)
                if value:
                    current_error = key
            elif current_contract is not None and current_contract['file'] in line and line.index(
                    current_contract['file']) == 0:
                (file, classname, line, column) = line.split(':')
                current_contract['errors'].append({
                    'line': int(line),
                    'column': int(column),
                    'message': current_error
                })
        if current_contract is not None:
            output.append(current_contract)
        return output

    def parseSarif(self, osiris_output_results):
        resultsList = []
        artifactsList = []
        logicalLocationsList = []
        rulesList = []

        for analysis in osiris_output_results["analysis"]:
            artifact = None
            logicalLocation = None

            for result in analysis["errors"]:
                ruleId = parseRuleIdFromMessage(result["message"])
                message = Message(text=parseMessage(result["message"]))
                level = parseLevel("warning")
                uri = parseUri(analysis["file"])
                locations = [
                    Location(physical_location=PhysicalLocation(artifact_location=ArtifactLocation(uri=uri),
                                                                region=Region(start_line=result["line"],
                                                                              start_column=result["column"])))
                    # Location(logical_locations=LogicalLocation(name=analysis["name"],kind="contract"))
                ]

                resultsList.append(Result(rule_id=ruleId,
                                          message=message,
                                          level=level,
                                          locations=locations))

                rule = ReportingDescriptor(id=ruleId,
                                           short_description=MultiformatMessageString(
                                               result["message"]))

                if isNotDuplicateRule(rule, rulesList):
                    rulesList.append(rule)

                artifact = Artifact(location=ArtifactLocation(uri=uri), source_language="Solidity")
                logicalLocation = LogicalLocation(name=analysis["name"], kind="contract")

            if artifact != None and isNotDuplicateArtifact(artifact, artifactsList): artifactsList.append(artifact)
            if logicalLocation != None: logicalLocationsList.append(logicalLocation)

        tool = Tool(driver=ToolComponent(name="Osiris", version="1.0", rules=rulesList,
                                         information_uri="https://github.com/christoftorres/Osiris",
                                         full_description=MultiformatMessageString(
                                             text="Osiris is an analysis tool to detect integer bugs in Ethereum smart contracts. Osiris is based on Oyente.")))

        run = Run(tool=tool, artifacts=artifactsList, logical_locations=logicalLocationsList, results=resultsList)

        return run
