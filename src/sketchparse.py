#!/usr/bin/env python

import sys
import traceback
import os
import zipfile
import tempfile
import json
import pyjq
import csv

from collections.abc import Mapping, Set, Sequence

helper = """========== HELP ==========

Summary:
sketchparse - simple sketch file parser.

It gets sketch file and produces output with all strings whose name begins with
the prefix \"%%\".

Usage:
sketchparse [-h|--help|help] [-i|--invert] input_file_name [-o output_file_name]

Options:
    -h
    --help
    help
        Produces this message.

    -i
    --invert
        It reverses the behavior of the program. This means that at the moment
        the input file should be a CSV file and the all strings in SKETCH file
        (output) will be replaced with values from input file.

        Warning!
        Must be passed before input_file_name.

    -o
        There is an optional value. If no output file is selected, the program
        will use the same name as the input file and just change the output
        file format.

Disclaimer:
It is assumed that the first row of the CSV file will always contain column
names.
"""


class ParseSketch:
    inputFile = None
    outputFile = None
    tempdir = None

    def __init__(self, args, invert=False, helper=''):
        self.helper=helper
        if not invert:
            if not self.parseArgs(args):
                self.terminate()
            if not self.inputFile or not self.outputFile:
                print('Please specify input/output files properly.')
                self.terminate()
        else:
            if not self.parseArgsForConverter(args):
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

    def parseArgsForConverter(self, args):
        def rreplace(s, old, new, occurrence=0):
            li = s.rsplit(old, occurrence)
            return new.join(li)

        if len(args) > 2:
            self.inputFile = args[2]
            if not self.inputFile.endswith('.csv'):
                print("Error: This is not a CSV file. Please enter a name for the input file with '.csv' format.")
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
                self.outputFile = rreplace(args[2], '.csv', '.sketch', 1)

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

    def unpackFile(self, invert=False):
        if not invert:
            sketchFile = self.inputFile
        else:
            sketchFile = self.outputFile
        print("Unpacking "+sketchFile+" file...")

        if not self.checkIfExsist(sketchFile):
            self.terminate(1)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                self.tempdir = tmpdir

            with zipfile.ZipFile(sketchFile, 'r') as zip_ref:
                zip_ref.extractall(self.tempdir)
        except Exception as err:
            msg = 'Error: There is a problem with unpacking sketch file.'
            raise Exception(msg).with_traceback(err.__traceback__)

        print("Done.\n")

    def packFile(self):
        def zipdir(path, ziph):
            # ziph is zipfile handle
            for root, dirs, files in os.walk(path):
                for file in files:
                    if sys.platform.startswith('linux'):
                        file_root = "/".join(root.split('/')[3:])
                    elif sys.platform.startswith('darwin'):
                        file_root = "/".join(root.split('/')[7:])

                    ziph.write(os.path.join(root, file), os.path.join(file_root, file))


        sketchFile = self.outputFile
        print("\nUpdating " +sketchFile+" file...")

        if not self.checkIfExsist(sketchFile):
            self.terminate(1)
        try:
            with zipfile.ZipFile(sketchFile, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipdir(self.tempdir, zipf)
        except Exception as err:
            msg = 'Error: There is a problem with zipping sketch file.'
            raise Exception(msg).with_traceback(err.__traceback__)
        print("Done.")


    def saveCSVOutput(self, data):
        print("Saving output...")
        deDumpingList = []

        with open(self.outputFile, "w") as output:
            writer = csv.writer(output, delimiter=',')
            writer.writerow(["label", "string"])

            for entry in data:
                if entry["label"] not in deDumpingList:
                    deDumpingList.append(entry["label"])
                    entry = [entry["label"], entry["string"]]
                    writer.writerow(entry)

        print("Done.")

    def parseCSVFile(self, data):
        if not self.checkIfExsist(data):
            self.terminate(1)
        try:
            with open(data) as csv_file:
                reader = csv.reader(csv_file, delimiter=',')
                return list(reader)[1:]
        except Exception as err:
            msg = 'Error: There is a problem with parsing CSV file.'
            raise Exception(msg).with_traceback(err.__traceback__)

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

    def recursivelyWalkPageObjects(self, page):
        string_types = (bytes, str) if str is bytes else (str, bytes)
        iteritems = lambda mapping: getattr(mapping, 'iteritems', mapping.items)()
        def objwalk(obj, path=(), memo=None):
            if memo is None:
                memo = set()
            iterator = None
            if isinstance(obj, Mapping):
                iterator = iteritems
            elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
                iterator = enumerate
            if iterator:
                if id(obj) not in memo:
                    memo.add(id(obj))
                    for path_component, value in iterator(obj):
                        for result in objwalk(value, path + (path_component,), memo):
                            yield result
                    memo.remove(id(obj))
            else:
                yield path, obj

        print("Parsing...")
        return objwalk(page)

    def updatePage(self, page, csvd):
        #csvd is a list of strings to replace (provided by CSV input file)
        print("Page opening...")
        with open(page) as json_file:
            content = json.load(json_file)

        for path, value in self.recursivelyWalkPageObjects(content):
            if path[-1] == "name" and value.startswith("%%"):
                parent = content
                for step in path[:-1]:
                    parent = parent[step]

                for csv_row in csvd:
                    if value == csv_row[0]:
                        parent["attributedString"]["string"] = csv_row[1]

        with open(page, "w") as json_file:
            json.dump(content, json_file)


    def terminate(self, exitcode=2):
        print('\n')
        print(self.helper)
        sys.exit(exitcode)

    def runExtractor(self):
        self.unpackFile()
        pages = self.getListOfPages()
        data = [self.parseSinglePage(page) for page in pages]
        data = [entry for i in data for entry in i]
        print("Done.\n")

        self.saveCSVOutput(data)

    def runConverter(self):
        inputFile = self.inputFile
        processingData = self.parseCSVFile(inputFile)
        self.unpackFile(True)
        pages = self.getListOfPages()
        for page in pages:
            self.updatePage(page, processingData)
        self.packFile()


if __name__ == '__main__':
    helper_info = "For help please run:\nsketchparse --help"
    args = sys.argv
    if '-h' in args or '--help' in args or 'help' in args:
        print(helper)
        sys.exit(0)
    elif '-i' in args or '--invert' in args:
        if args[1] == '-i' or args[1] == '--invert':
            converter = ParseSketch(args, invert=True, helper=helper_info)
            converter.runConverter()
        else:
            print("Error: -i or --invert flag passed in wrong place.")
            print("Must be passed before input_file_name.\n")
            print(helper_info)
            sys.exit(2)
    else:
        parser = ParseSketch(args, helper=helper_info)
        parser.runExtractor()
