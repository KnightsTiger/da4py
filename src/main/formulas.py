#!/usr/bin/env python
# -*- coding:utf-8 -*-
##
## variablesGenerator.py
##
##  Created on: September, 2019
##      Author: Boltenhagen Mathilde
##      E-mail: boltenhagen lsv . fr
##
##
##  Translation of Darksider in Ocaml by Thomas Chatain
##

'''

This file contains a set of classes of boolean formulas :

- Qbf_formula : Quantified boolean formulas
- Operator : mother class of OR(positives, negatives, formulas) and AND(positives, negatives, formulas)

'''

# needed for abstract methods
from abc import ABCMeta, abstractmethod

# number of variables, used in clausesToCnf translation
NB_VARS = 0

class Qbf_formula:
    '''
    Abstract class
    Quantified boolean formulas
    '''
    __metaclass__ = metaclass = ABCMeta

    @abstractmethod
    def simplify(self):
        pass

    @abstractmethod
    def negation(self):
        pass


class Operator(Qbf_formula):
    '''
     Mother class of OR(positives, negatives, formulas) and AND(positives, negatives, formulas)
    '''

    def __init__(self, type, positiveVariables, negativeVariables, qbf_formulas):
        '''
        :param type (string) : "AND" or "OR"
        :param positiveVariables (list of int)
        :param negatieVariables (list of int)
        :param qbf_formulas (list of QBF)
        '''
        self.type = type
        self.positiveVariables = positiveVariables
        self.negativeVariables = negativeVariables
        self.qbf_formulas = qbf_formulas

    def simplify(self):
        '''
        Notice that this function don't work well :
        Tests on number of variables show larger results when this function was used
        :return: QBF_formulas (only Operator)
        '''
        if len(self.qbf_formulas) == 0:
            return self
        if len(self.qbf_formulas) == 1 and len(self.positiveVariables) == 0 and len(self.negativeVariables) == 0:
            formula = self.qbf_formulas[0].simplify()
            return formula

        newQbflist = []
        for qbf in self.qbf_formulas:
            if qbf.type == self.type:
                self.negativeVariables += qbf.negativeVariables
                self.positiveVariables += qbf.positiveVariables
                newQbflist += qbf.qbf_formulas
            else:
                newQbflist.append(qbf)
        simplifiedQbflist = []
        for qbf in newQbflist:
            formula = qbf.simplify()
            simplifiedQbflist.append(formula)
        if self.type == "AND":
            formula = And(self.positiveVariables, self.negativeVariables, simplifiedQbflist)
            return formula
        if self.type == "OR":
            formula = Or(self.positiveVariables, self.negativeVariables, simplifiedQbflist)
            return formula

    def negation(self):
        newQbflist = [qbf.negation() for qbf in self.qbf_formulas]
        if self.type == "AND":
            return Or(self.negativeVariables, self.positiveVariables, newQbflist)
        if self.type == "OR":
            return And(self.negativeVariables, self.positiveVariables, newQbflist)

    @abstractmethod
    def distributeImplication(self, var):
        pass

    def operatorToCnf(self, nbVars):
        '''
        SAT solvers need list of CNF clauses
        :param nbVars (int) : number of variables will increase
        :return list * list * int : CNF clauses
        '''
        global NB_VARS
        NB_VARS = nbVars
        return self.aux_operatorToCnf()

    @abstractmethod
    def aux_operatorToCnf(self):
        '''
        Specific function depending on the operator
        :return list * list * int : CNF clauses
        '''
        pass

    def __repr__(self, variablesGenerator=None, time=0):
        '''
        Debug display of the formula
        :param variablesGenerator: names of the variables
        :param time: increases the <tab> display
        :return (string)
        '''
        if variablesGenerator == None:
            return self.type + str(self.positiveVariables) + str(self.negativeVariables) + str(self.qbf_formulas)
        str_of_formulas = ['\n' + q.__repr__(variablesGenerator, time + 1) for q in self.qbf_formulas]
        str_of_positivesVariables = [variablesGenerator.getVarName(n)
                                     if variablesGenerator.getVarName(n) is not None else n for n in
                                     self.positiveVariables]
        str_of_negativeVariables = [variablesGenerator.getVarName(n)
                                    if variablesGenerator.getVarName(n) is not None else n for n in
                                    self.negativeVariables]
        return "\t" * time + self.type + "( [" \
               + ', '.join(str_of_positivesVariables) + "], [" \
               + ', '.join(str_of_negativeVariables) + "], " \
               + ' '.join(str_of_formulas) + ")"


class And(Operator):
    def __init__(self, positiveVariables, negativeVariables, qbf_formulas):
        self.type = "AND"
        self.positiveVariables = positiveVariables
        self.negativeVariables = negativeVariables
        self.qbf_formulas = qbf_formulas

    def distributeImplication(self, var):
        temp = [Or([positiveVariable], [var], []) for positiveVariable in self.positiveVariables] + \
               [Or([], [negativeVariable, var], []) for negativeVariable in self.negativeVariables] + \
               [Or([], [var], [formula]) for formula in self.qbf_formulas]
        self.qbf_formulas = temp
        self.positiveVariables = []
        self.negativeVariables = []

    def aux_operatorToCnf(self):
        dnfPositiveVariables = []
        dnfNegativeVariables = []
        for v in self.positiveVariables:
            dnfPositiveVariables.append([v])
        for v in self.negativeVariables:
            dnfNegativeVariables.append([v * -1])
        left = []
        for formula in self.qbf_formulas:
            cnf = formula.aux_operatorToCnf()
            left += cnf
        return dnfPositiveVariables + dnfNegativeVariables + left


class Or(Operator):
    def __init__(self, positiveVariables, negativeVariables, qbf_formulas):
        self.type = "OR"
        self.positiveVariables = positiveVariables
        self.negativeVariables = negativeVariables
        self.qbf_formulas = qbf_formulas

    def getpositiveVariables(self):
        return self.positiveVariables

    def getnegativeVariables(self):
        return self.negativeVariables

    def distributeImplication(self, var):
        self.negativeVariables.append(var)

    def aux_operatorToCnf(self):
        if len(self.qbf_formulas)==1 and self.qbf_formulas[0].type == "OR" and len(self.qbf_formulas[0].getpositiveVariables())==0\
                and len(self.qbf_formulas[0].getnegativeVariables())==0:
            clauses = Or(self.positiveVariables,self.negativeVariables,self.qbf_formulas[0].qbf_formulas).aux_operatorToCnf()
            return  clauses
        else:
            global NB_VARS
            newVariables = []
            for numVariable in range(NB_VARS, NB_VARS + len(self.qbf_formulas)):
                newVariables.append(numVariable)
            dnf = self.positiveVariables + newVariables + [v * -1 for v in self.negativeVariables]
            for i in range(0, len(self.qbf_formulas)):
                # distribute implication
                if self.qbf_formulas[i].type == "OR":
                    self.qbf_formulas[i].negativeVariables = self.qbf_formulas[i].negativeVariables + [NB_VARS + i]
                else:
                    var = NB_VARS + i
                    newListOfFormulas = []
                    for positiveVariable in self.qbf_formulas[i].positiveVariables:
                        newListOfFormulas.append(Or([positiveVariable], [var], []))
                    for negativeVariable in self.qbf_formulas[i].negativeVariables:
                        newListOfFormulas.append(Or([], [negativeVariable, var], []))
                    for formula in self.qbf_formulas[i].qbf_formulas:
                        newListOfFormulas.append(Or([], [var], [formula]))
                    self.qbf_formulas[i].qbf_formulas = newListOfFormulas
                    self.qbf_formulas[i].negativeVariables = []
                    self.qbf_formulas[i].positiveVariables = []
            NB_VARS += len(self.qbf_formulas)
            if len(self.qbf_formulas) == 0:
                return [dnf]
            else:
                clauses = And([], [], self.qbf_formulas).aux_operatorToCnf()
                clauses.append(dnf)
                return clauses