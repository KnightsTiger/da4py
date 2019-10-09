#!/usr/bin/env python
# -*- coding:utf-8 -*-
##
## variablesGenerator.py
##
##  Created on: September, 2019
##      Author: Boltenhagen Mathilde
##      E-mail: boltenhagen lsv . fr
##

'''

The ConformanceArtefacts class is a factory class that can run the different artefacts:
    -   Multi-Alignment
    -   Anti-Alignment

Two distances are available with specific formula reduction for anti-alignment and multi-alignment. The exact formulas
are also implemented but shouldn't be used. They are presented for experimentations.

Scientific paper : _Encoding Conformance Checking Artefacts in SAT_
By : Mathilde Boltenhagen, Thomas Chatain, Josep Carmona

'''

import time

from pm4py.objects.petri.petrinet import PetriNet
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF

from src.main.distancesToFormulas import hamming_distance_per_trace_to_SAT, edit_distance_per_trace_to_SAT
from src.main.formulas import And
from src.main.logToFormulas import log_to_SAT
from src.main.pnToFormulas import petri_net_to_SAT
from src.main import variablesGenerator as vg

# a wait transition is added to complete words, :see __add_wait_net()
WAIT_TRANSITION = "w"

# our boolean formulas depends on variables, see our paper for more information
BOOLEAN_VAR_MARKING_PN = "m_ip"
BOOLEAN_VAR_FIRING_TRANSITION_PN = "tau_it"
BOOLEAN_VAR_TRACES_ACTIONS = "lambda_jia"
BOOLEAN_VAR_EDIT_DISTANCE = "djiid"

# SAT solver allows to add weights on clauses to reduce or maximize
WEIGHT_ON_CLAUSES_TO_REDUCE = -10

# two distances are available
HAMMING_DISTANCE = "hamming"
EDIT_DISTANCE = "edit"

# three implementations have been created
MULTI_ALIGNMENT = "multi"
ANTI_ALIGNMENT = "anti"
EXACT_ALIGNMENT = "exact"


class ConformanceArtefacts:
    '''

    The ConformanceArtefacts class is a factory class that can run the different artefacts:
    -   Multi-Alignment
    -   Anti-Alignment
    ( and the exact distance )

    '''

    def __init__(self, size_of_run, max_d=10, distance=EDIT_DISTANCE, solver="g4"):
        '''
        Conformance artefact share some initialisation
        :param size_of_run (int) : maximal size of run, too limit the run when there are loops
        :param max_d (int) :
        :param distance (string) : value = HAMMING_DISTANCE or EDIT_DISTANCE
        :param solver: one of the SAT solver of the librairy pysat
        '''
        self.__size_of_run = size_of_run
        self.__max_d = max_d
        self.__distance_type = distance
        self.__solver = solver

    def multiAlignment(self, net, m0, mf, traces, silent_transition="tau"):
        '''
        The multiAlignment method takes a petri net and a log and compute the SAT formulas to get a run of the model
        that is the closest one to all the traces of the log.
        :param net (Petrinet) : model
        :param m0 (marking) : initial marking
        :param mf (marking) : final marking
        :param traces (pm4py.objects.log) : traces
        :param silent_transition (string) : transition with this label will not increase the distances
        :return:
        '''
        self.__net = net
        # transforms the model and the log to SAT formulas
        initialisationFormulas, wait_transition = self.__artefactsInitialisation(m0, mf, traces)

        # computes the distance for multi-alignment
        distanceFormula = self.__compute_distance(MULTI_ALIGNMENT, wait_transition)

        # solve the formulas
        wncf = self.__createWncf(initialisationFormulas, distanceFormula, MULTI_ALIGNMENT)
        self.__solveWncf(wncf)
        return 0

    def antiAlignment(self, net, m0, mf, traces, silent_transition="tau"):
        '''
        The antiAlignment method takes a petri net and a log and compute the SAT formulas to get a run of the model
        that is as far as possible to any traces of the log.
        :param net (Petrinet) : model
        :param m0 (marking) : initial marking
        :param mf (marking) : final marking
        :param traces (pm4py.objects.log) : traces
        :param silent_transition (string) : transition with this label will not increase the distances
        :return:
        '''
        self.__net = net
        # transforms the model and the log to SAT formulas
        initialisationFormulas, wait_transition = self.__artefactsInitialisation(m0, mf, traces)

        # computes the distance for multi-alignment
        distanceFormula = self.__compute_distance(ANTI_ALIGNMENT, wait_transition)

        # solve the formulas
        wncf = self.__createWncf(initialisationFormulas, distanceFormula, ANTI_ALIGNMENT)
        self.__solveWncf(wncf)
        return 0

    def exactAlignment(self, net, m0, mf, traces, silent_transition="tau"):
        '''
        # TODO : be more precised
       The exactAlignment method takes a petri net and a log and compute the SAT formulas to get a run of the model
       that is the closest one to all the traces of the log. Notice that this function is presented for experimentation
       only.
       :param net (Petrinet) : model
       :param m0 (marking) : initial marking
       :param mf (marking) : final marking
       :param traces (pm4py.objects.log) : traces
       :param silent_transition (string) : transition with this label will not increase the distances
       :return:
       '''
        initialisationFormulas, wait_transition = self.__artefactsInitialisation(m0, mf, traces)
        distanceFormula = self.__compute_distance(EXACT_ALIGNMENT, wait_transition)
        wncf = self.__createWncf(initialisationFormulas, distanceFormula, EXACT_ALIGNMENT)
        self.__solveWncf(wncf)
        return 0

    def __artefactsInitialisation(self, m0, mf, traces):
        '''
        The initialisation of all the artefacts :
            - launches a VariablesGenerator to creates the variables numbers
            - translates the model into formulas
            - translates the log into formulas
        :param (marking) : initial marking
        :param mf (marking) : final marking
        :param traces (pm4py.objects.log) : traces
        :return:
        '''
        # this variable (__variables) memorises the numbers of the boolean variables of the formula
        self.__variables = vg.VariablesGenerator()

        # we add a "wait" transition to complete the words
        wait_transition = self.__add_wait_net()

        start = time.time()
        # the model is translated to a formula
        pn_formula, places, self.__transitions = petri_net_to_SAT(self.__net, m0, mf, self.__variables,
                                                                  self.__size_of_run,
                                                                  label_m=BOOLEAN_VAR_MARKING_PN,
                                                                  label_t=BOOLEAN_VAR_FIRING_TRANSITION_PN)
        # the log is translated to a formula
        log_formula, traces = log_to_SAT(traces, self.__transitions, self.__variables, self.__size_of_run,
                                         wait_transition)
        self.__traces = traces
        return [pn_formula, log_formula], wait_transition

    def __compute_distance(self, artefact, wait_transition):
        if self.__distance_type == HAMMING_DISTANCE:
            return hamming_distance_per_trace_to_SAT(artefact, self.__transitions, self.__variables, len(self.__traces),
                                                     self.__size_of_run)
        elif self.__distance_type == EDIT_DISTANCE:
            return edit_distance_per_trace_to_SAT(artefact, self.__transitions, self.__variables, len(self.__traces),
                                                  self.__size_of_run,
                                                  wait_transition, self.__max_d)
        else:
            print("TODO")

    def __createWncf(self, initialisationFormulas, distanceFormula, artefactForMinimization):
        '''
        This method creates the wncf formulas with the weighted variables depending on the distance and artefact.
        :param initialisationFormulas: @see __artefactsInitialisation
        :param distanceFormula: @see __compute_distance
        :param artefactForMinimization: MULTI_ALIGNMENT or ANTI_ALIGNMENT or EXACT_ALIGNMENT
        :return:
        '''
        formulas = initialisationFormulas + distanceFormula
        full_formula = And([], [], formulas)
        cnf = full_formula.operatorToCnf(self.__variables.iterator)
        print(self.__variables.iterator)
        wcnf = WCNF()
        wcnf.extend(cnf)
        # weights of variables depends on artefact
        weightsOnVariables = -1 if artefactForMinimization != ANTI_ALIGNMENT else 1

        # weighted variables for edit distance are d_j,n,n,d
        if self.__distance_type == EDIT_DISTANCE:
            for j in range(0, len(self.__traces)):
                for d in range(1, self.__max_d + 1):
                    wcnf.append([weightsOnVariables * self.__variables.getVarNumber(BOOLEAN_VAR_EDIT_DISTANCE,
                                                                                    [j, self.__size_of_run,
                                                                                     self.__size_of_run, d])],
                                WEIGHT_ON_CLAUSES_TO_REDUCE)

        # weighted variables for edit distance are d_j,i
        elif self.__distance_type == HAMMING_DISTANCE:
            for j in range(0, len(self.__traces)):
                for i in range(1, self.__size_of_run + 1):
                    wcnf.append([weightsOnVariables * self.__variables.getVarNumber(BOOLEAN_VAR_EDIT_DISTANCE, [j, i])],
                                WEIGHT_ON_CLAUSES_TO_REDUCE)
        formula_time = time.time()
        return wcnf

    def __solveWncf(self, wcnf):
        '''
        This method launches the SAT solver.
        :param wcnf: formulas
        :return:
        '''
        solver = RC2(wcnf, solver=self.__solver)
        solver.compute()
        end_solver = time.time()
        self.__model = solver.model

    def __add_wait_net(self):
        '''
        Words don't have the same length. To compare them we add a "wait" transition at the end of the model and the
        traces.
        :return:
        '''
        wait_transition = PetriNet.Transition(WAIT_TRANSITION, WAIT_TRANSITION)
        for place in self.__net.places:
            if len(place.out_arcs) == 0:
                arcIn = PetriNet.Arc(place, wait_transition)
                arcOut = PetriNet.Arc(wait_transition, place)
                self.__net.arcs.add(arcIn)
                self.__net.arcs.add(arcOut)
                wait_transition.in_arcs.add(arcIn)
                wait_transition.out_arcs.add(arcOut)
                place.out_arcs.add(arcIn)
                place.in_arcs.add(arcOut)
        self.__net.transitions.add(wait_transition)
        return wait_transition

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Here starts the dark code : code that should be redo
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

    def getRun(self):
        '''
        NO DESCRIPTION FOR BAD METHODS
        :return:
        '''
        # TODO TRY/EXCEPT EVERYTHING HERE IS TO RE DO
        run = "<"
        for var in self.__model:
            if self.__variables.getVarName(var) != None and self.__variables.getVarName(var).startswith(
                    BOOLEAN_VAR_FIRING_TRANSITION_PN):
                index = self.__variables.getVarName(var).split("]")[0].split(",")[1]
                i = self.__variables.getVarName(var).split("[")[1].split(",")[0]
                run += " (" + i + ", " + str(self.__transitions[int(index)]) + "),"
        run += ">"
        return run

    def getTracesWithDistances(self):
        '''
        NO DESCRIPTION FOR BAD METHODS
        :return:
        '''
        # TODO TRY/EXCEPT EVERYTHING HERE IS TO RE DO
        traces = "<"
        for var in self.__model:
            if self.__variables.getVarName(var) != None and self.__variables.getVarName(var).startswith(
                    BOOLEAN_VAR_TRACES_ACTIONS):
                index = self.__variables.getVarName(var).split("]")[0].split(",")[2]
                i = self.__variables.getVarName(var).split("[")[1].split(",")[1]
                if int(i) == 1:
                    traces += "\n"
                traces += " (" + i + ", " + str(self.__transitions[int(index)]) + "),"

        if self.__distance_type == EDIT_DISTANCE:
            for l in range(0, len(self.__traces)):
                max = 0
                for d in range(0, self.__max_d + 1):
                    if self.__variables.getVarNumber(BOOLEAN_VAR_EDIT_DISTANCE,
                                                     [l, self.__size_of_run, self.__size_of_run, d]) in self.__model:
                        max = d
                print(l, " :", max)
        if self.__distance_type == HAMMING_DISTANCE:
            for l in range(0, len(self.__traces)):
                sum = 0
                for i in range(1, self.__size_of_run + 1):
                    if self.__variables.getVarNumber(BOOLEAN_VAR_EDIT_DISTANCE, [l, i]) in self.__model:
                        sum += 1
                print(l, " :", sum)
        return traces