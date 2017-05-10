#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2016 David Emms
#
# This program (OrthoFinder) is distributed under the terms of the GNU General Public License v3
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  
#  When publishing work that uses OrthoFinder please cite:
#      Emms, D.M. and Kelly, S. (2015) OrthoFinder: solving fundamental biases in whole genome comparisons dramatically 
#      improves orthogroup inference accuracy, Genome Biology 16:157
#
# For any enquiries send an email to David Emms
# david_emms@hotmail.comhor: david

import os
import json
import shutil


import util

class InvalidEntryException(Exception):
    pass

class Method(object):
    def __init__(self, name, config_dict):
        if 'cmd_line' in config_dict:
            self.cmd = config_dict['cmd_line']
        else:
            print("WARNING: Incorrecty formatted configuration file entry: %s" % name)
            print("'cmd_line' entry is missing")
            raise InvalidEntryException
        if 'ouput_filename' in config_dict:
            self.non_default_outfn = config_dict['ouput_filename'] 
        else:
            self.non_default_outfn = None

class ProgramCaller(object):
    def __init__(self, configure_file):
        self.msa = dict()
        self.tree = dict()
        if configure_file == None:
            return
        if not os.path.exists(configure_file):
            print("WARNING: Configuration file, '%s', does not exist. No user-confgurable multiple sequence alignment or tree inference methods have been added.\n" % configure_file)
            return
        with open(configure_file, 'rb') as infile:
            try:
                d = json.load(infile)
            except ValueError:
                print("WARNING: Incorrecty formatted configuration file %s" % configure_file)
                print("File is not in .json format. No user-confgurable multiple sequence alignment or tree inference methods have been added.\n")
                return
            for name, v in d.items():
                if name == "__comment": continue
                if " " in name:
                    print("WARNING: Incorrecty formatted configuration file entry: %s" % name)
                    print("No space is allowed in name: '%s'" % name)
                    continue
                    
                if 'program_type' not in v:
                    print("WARNING: Incorrecty formatted configuration file entry: %s" % name)
                    print("'program_type' entry is missing")
                try:
                    if v['program_type'] == 'msa':
                        self.msa[name] = Method(name, v)
                    elif v['program_type'] == 'tree':
                        self.tree[name] = Method(name, v)
                    else:
                        print("WARNING: Incorrecty formatted configuration file entry: %s" % name)
                        print("'program_type' should be 'msa' or 'tree', got '%s'" % v['program_type'])
                except InvalidEntryException:
                    pass
    
    def Add(self, other):
        self.msa.update(other.msa)
        self.tree.update(other.tree)
    
    def ListMSAMethods(self):
        return [key for key in self.msa]
    def ListTreeMethods(self):
        return [key for key in self.tree]

    def GetMSAMethodCommand(self, method_name, infilename, outfilename_proposed, identifier):
        return self._GetCommand('msa', method_name, infilename, outfilename_proposed, identifier)
    def GetTreeMethodCommand(self, method_name, infilename, outfilename_proposed, identifier):
        return self._GetCommand('tree', method_name, infilename, outfilename_proposed, identifier)
    
    def GetMSACommands(self, method_name, infn_list, outfn_list, id_list):        
        return [self.GetMSAMethodCommand(method_name, infn, outfn, ident) for infn, outfn, ident in zip(infn_list, outfn_list, id_list)]
    def GetTreeCommands(self, method_name, infn_list, outfn_list, id_list):        
        return [self.GetTreeMethodCommand(method_name, infn, outfn, ident) for infn, outfn, ident in zip(infn_list, outfn_list, id_list)]
    
    def CallMSAMethod(self, method_name, infilename, outfilename, identifier):
        return self._CallMethod('msa', method_name, infilename, outfilename, identifier)
    def CallTreeMethod(self, method_name, infilename, outfilename, identifier):
        return self._CallMethod('tree', method_name, infilename, outfilename, identifier)        
        
    def TestMSAMethod(self, working_dir, method_name):
        return self._TestMethod(working_dir, 'msa', method_name)
    def TestTreeMethod(self, working_dir, method_name):
        return self._TestMethod(working_dir, 'tree', method_name)
    
    def _CallMethod(self, method_type, method_name, infilename, outfilename, identifier):
        cmd, outfilename = self._GetCommand(method_type, method_name, infilename, outfilename, identifier)
#        print(cmd)
        util.RunCommand(cmd, shell=True, qHideOutput=False)
        return outfilename
    
    def _TestMethod(self, working_dir, method_type, method_name):
        d = working_dir + "temp_83583209132/"
        os.mkdir(d)
        try:
            infn = self._WriteTestSequence(d)
            propossed_outfn = infn + "output.txt"
            outfilename = self._CallMethod(method_type, method_name, infn, propossed_outfn, "test")
            success = os.path.exists(outfilename)
        except:
            shutil.rmtree(d)
            raise
        shutil.rmtree(d)
        return success

    def _ReplaceVariables(self, instring, infilename, outfilename, identifier):
        path, basename = os.path.split(infilename)
        return instring.replace("INPUT", infilename).replace("OUTPUT", outfilename).replace("IDENTIFIER", identifier).replace("BASENAME", basename).replace("PATH", path)  

    def _GetMethodTypeName(self, method_type):
        if method_type == 'msa':
            return "multiple sequence alignment"
        elif method_type == 'tree':
            return "tree"
        else:
            raise NotImplementedError
        
    def _GetCommand(self, method_type, method_name, infilename, outfilename_proposed, identifier):
        if method_type == 'msa':
            dictionary = self.msa
        elif method_type == 'tree':
            dictionary = self.tree
        else:
            raise NotImplementedError
        if method_name not in dictionary:
            raise Exception("No %s method called '%s'" % (self._GetMethodTypeName(method_type), method_name))
        method_parameters = dictionary[method_name]
        cmd = self._ReplaceVariables(method_parameters.cmd, infilename, outfilename_proposed, identifier)
        outfilename = outfilename_proposed
        if method_parameters.non_default_outfn:
            outfilename = self._ReplaceVariables(method_parameters.non_default_outfn, infilename, outfilename_proposed, identifier)
        return cmd, outfilename
        
    def _WriteTestSequence(self, working_dir):
        fn = working_dir + "Test.fa"
        with open(fn, 'wb') as outfile:
            outfile.write(">a\nST\n>b\nKL\n>c\nSL\n>d\nKT")
        return fn
    
#    def TestMSAMethods(self, working_dir):
#        methods = self.ListMSAMethods()
#        successes = []
#        messages = []
#        for method in methods:
#            success, message = self.TestMSAMethod(working_dir, method)
#            successes.append(success)
#            messages.append(message)
#        return methods, successes, messages          
#   
#    def TestTreeMethods(self, working_dir):
#        methods = self.ListTreeMethods()
#        successes = []
#        messages = []
#        for method in methods:
#            success, message = self.TestTreeMethod(working_dir, method)
#            successes.append(success)
#            messages.append(message)
#        return methods, successes, messages
                   