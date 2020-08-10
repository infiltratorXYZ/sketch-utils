#!/usr/bin/env python

import sys
import traceback
import os
import zipfile
import tempfile
import json
import pyjq
import csv

# TODO: DE-DUMPING

helper = """
sketchparse - simple sketch file parser.
It gets sketch file and produces output with all strings whose name begins with the prefix \"%%\".

Usage:
sketchparse [-h|--help|help] input_file_name.sketch [-o output_file_name]
"""


class ParseSketch:
    inputFile = None
    outputFile = None
    tempdir = None
    unpacked = False

    def __init__(self, args):
        if not self.parseArgs(args):
            self.terminate()
        if not self.inputFile or not self.outputFile:
            print('Please specify input/output files properly.')
            self.terminate()

    def parseArgs(self, args):
        def rreplace(s, old, new, occurrence=0):
            li = s.rsplit(old, occurrence)
            return new.join(li)

        if len(args) > 1:
            self.inputFile = args[1]
            if not self.inputFile.endswith('.sketch'):
                print(
                    "Error: This is not a sketch file. Please enter a name for the input file with '.sketch' format.")
                return False

            isOutput = False
            for arg in args:
                if arg == '-o':
                    isOutput = True
                    if arg == args[-1]:
                        print('Error: Please specify the output file.')
                        return False

                    continue
                elif isOutput:
                    self.outputFile = arg
                    break
            if not isOutput:
                self.outputFile = rreplace(args[1], '.sketch', '.csv', 1)

        else:
            print("Error: Please specify the input file."),
            return False

        return True

    def checkIfExsist(self, iFile=None):
        if not iFile:
            iFile = self.inputFile
        if os.path.isfile(iFile):
            return True
        print("Error: File '"+iFile+"' doesn't exist.")
        return False

    def unpackFile(self):
        if not self.checkIfExsist():
            self.terminate(1)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                self.tempdir = tmpdir

            with zipfile.ZipFile(self.inputFile, 'r') as zip_ref:
                zip_ref.extractall(self.tempdir)
        except Exception as err:
            msg = 'Error: There is a problem with unpacking sketch file.'
            raise Exception(msg).with_traceback(err.__traceback__)

    def saveCSVOutput(self, data):
        print("Saving output...")

        with open(self.outputFile, "w") as output:
            writer = csv.writer(output, delimiter=',')
            writer.writerow(["label", "string"])

            for entry in data:
                entry = [entry["label"], entry["string"]]
                writer.writerow(entry)

        print("Done.")

    def getListOfPages(self):
        print("Pages loading...")
        nameList = os.listdir(self.tempdir+'/pages')
        pathList = [self.tempdir+'/pages/'+page for page in nameList]

        return pathList

    def parseSinglePage(self, page):
        print("Page opening...")
        with open(page) as json_file:
            data = json.load(json_file)

        print("Parsing...")
        jqFilter = '[recurse(.layers[]?) | {label:.name, string: .attributedString.string}] | .[] | select(any(.label; startswith("%%")))'
        parsedData = pyjq.all(jqFilter, data)

        return parsedData

    def terminate(self, exitcode=2):
        sys.exit(exitcode)

    def runExtractor(self):
        self.unpackFile()
        pages = self.getListOfPages()
        data = [self.parseSinglePage(page) for page in pages]
        data = [entry for i in data for entry in i]
        print("Done.\n")

        self.saveCSVOutput(data)


if __name__ == '__main__':

    args = sys.argv
    if '-h' in args or '--help' in args or 'help' in args:
        print(helper)
        sys.exit(0)
    parser = ParseSketch(args)
    parser.runExExtractor()
