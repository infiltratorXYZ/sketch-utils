#!/usr/bin/env python

import sys, traceback
import os
import zipfile
import tempfile

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
                print("Error: This is not a sketch file. Please enter a name for the input file with '.sketch' format.")
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

        import os
        print(os.listdir(self.tempdir+'/pages'))
    def terminate(self, exitcode=2):
        sys.exit(exitcode)


if __name__ == '__main__':
    args = sys.argv
    parser = ParseSketch(args).unpackFile()
    tempfile._allocate_lock


