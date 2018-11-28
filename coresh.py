import random
import re
import subprocess
import copy
import os
import scipy.stats

from graphviz import Graph as Gr
from tempfile import TemporaryFile, _TemporaryFileWrapper
from datetime import datetime
from z3 import *

class Vertex:

    def __init__(self, name):

        self.name = name

class Edge:

    def __init__(self, name, size):

        self.name = name
        self.size = size

class EdgeInstance:

    def __init__(self, edge, args):

        self.edge = edge
        self.args = args

#Objects of class HGraph represent a single specific hypergraph and the actions you can perform on it.
class HGraph:

    #It has to be instantiated by either parsing a hypergraph-structure from a file, copying a preexisting HGraph instance or generation a new one according to specified values.
    def __init__(self, **kwargs):

        if not len(kwargs)==1 or not list(kwargs.keys()) <= ["parse", "copy", "gen", ]:
            raise Exception("You have to specify exactly one way to instantiate Graph at a time. Either parse or copy or generate a Graph:\ng = HGraph(parse=r\"C:\CoReS\hgraphs\hgraph1.txt\")\nh = HGraph(copy=g.hgraph)\ng = HGraph(gen=(64,2,2,1))")
        elif "parse" in kwargs:
            if (isinstance(kwargs["parse"], str) and os.path.isfile(kwargs["parse"])) or isinstance(kwargs["parse"], _TemporaryFileWrapper):
                self.hgraph = self._parse(kwargs["parse"])
            else:
                raise Exception("The parameter parse has to be an absolute and valid filepath in the form of a string. E.g.: g = HGraph(parse=r\"C:\CoReS\hgraphs\hgraph1.txt\")")
        elif "copy" in kwargs:
            if isinstance(kwargs["copy"], HGraph):
                self.hgraph = copy.deepcopy(kwargs["copy"].hgraph)
            else:
                raise Exception("The graph parameter should only be used to copy other preexisting HGraph instances. E.g.: h = HGraph(copy=g)")
        elif "gen" in kwargs:
            if ((isinstance(kwargs["gen"], tuple) and len(kwargs["gen"])==4) and
                (isinstance(kwargs["gen"][0], int) and kwargs["gen"][0]>=0) and
                (isinstance(kwargs["gen"][1], int) and kwargs["gen"][1]>=0) and
                ((isinstance (kwargs["gen"][2], int) or isinstance(kwargs["gen"][2], float)) and kwargs["gen"][2]>=0) and
                ((isinstance (kwargs["gen"][3], int) or isinstance(kwargs["gen"][3], float)) and kwargs["gen"][3]>=0)):
                self.hgraph = self._generate(*kwargs["gen"])
            else:
                raise Exception("The gen parameter has to be of the form of a tuple (vertex_n, edge_n, avg_edge_args, connectivity) with: int:vertex_n>=0, int:edge_n>=0, float:avg_edge_args>=0 and float:connectivity>=0. For details see github. E.g.: g = HGraph(gen=(8,2,2,1))")

    @staticmethod
    def _parse(target):

        #For tools using this program as a submodule, it may be usefull to be able to parse from virtual files (TemporaryFile) instead of actual files.
        if isinstance(target, str):
            data = open(target, "r")
        elif isinstance(target, _TemporaryFileWrapper):
            data = target

        regex = re.fullmatch(r"V:(?P<vertices>(\n[a-z0-9_.]+( [a-z0-9_.]+)*)?)\nL:(?P<labels>(\n[a-zA-Z_]+ \d+)*)\nE:(?P<edges>(\n[a-zA-Z_]+( [a-z0-9_.]+)*)*)", data.read())

        if regex == None:
            raise Exception("The content of the input file does not match the required syntax. Please consult the github for advice.")

        vertices = regex.group("vertices")
        labels = regex.group("labels")
        edges = regex.group("edges")

        vertices = re.split(" ", vertices.lstrip("\n"))
        if vertices == [""]:
            vertices = []
        if not _unique_list(vertices):
            raise Exception("There can be no repetition in the listing of the vertices, they have to be unique.")

        labels = re.split("\n", labels.lstrip("\n"))
        if labels == [""]:
            labels = []
        labels = [n.split() for n in labels]
        if not _unique_list([n[0] for n in labels]):
            raise Exception("There can be no repetition in the naming of the labels, they have to be unique.")
        labels = {n[0]: int(n[1]) for n in labels}

        edges = re.split("\n", edges.lstrip("\n"))
        if edges == [""]:
            edges = []
        edges = set(edges)
        edges = [n.split() for n in edges]
        for n in edges:
            if not n[0] in labels:
                raise Exception("Label \"{}\" of the listed edge \"{}\" is not part of the listing of labels.".format(n[0], " ".join(n)))
            if not len(n[1:])==labels[n[0]]:
                raise Exception("The number of arguments for the listed edge \"{}\" does not match the arrity of label {}, it should be {}.".format(" ".join(n), n[0], labels[n[0]]))
            for m in n[1:]:
                if not m in vertices:
                    raise Exception("Argument \"{}\" in the listed edge \"{}\" is not part of the listing of vertices.".format(m, " ".join(n)))

        vertices = {n: Vertex(n) for n in vertices}

        labels = {n: Edge(n, labels[n]) for n in labels}

        edges = [EdgeInstance(labels[n[0]], [vertices[m] for m in n[1:]]) for n in edges]

        return [list(vertices.values()),edges]

    #Used to generate randomized hypergraphs according to some provided values.
    #vertex_n for the actual amount of vertices in the hypergraph.
    #edge_n for the amount of different labels in a hypergraph. Note that there can be labels for which no edge ends up being generated.
    #avg_edge_args for the expected value of the average arrity of the labels. Actual arrities range from 0 to vertex_n and are distributed according to a binomial distribution B(vertex_n, avg_edge_args/vertex_n).
    #connectivity used to describe the expected value of "the connectivity" of the resulting graph in some sense. For details see github.
    @staticmethod
    def _generate(vertex_n, edge_n, avg_edge_args, connectivity):

        #Note: scipy.stats.binom.ppf can fail for larger vertex_n and/or arrities.
        #Since _generate is only supposed to be used for testing/benchmarking and not integral to calculating the core, we do not handle this issue at all at this point.

        vertices = [Vertex(str(n)) for n in range(vertex_n)]

        edges = [Edge(_charify(n), int(scipy.stats.binom.ppf(random.random(),vertex_n,avg_edge_args/vertex_n))) for n in range(edge_n)]

        edge_insts = []

        for n in edges:
            if n.size == 0:
                edge_insts.append(EdgeInstance(n, []))
            else:
                cands = []
                size = int(scipy.stats.binom.ppf(random.random(), vertex_n**n.size, min(1,((connectivity*2*vertex_n)/(n.size*edge_n))/(vertex_n**n.size))))
                while len(cands)<size:
                    cand = EdgeInstance(n, random.choices(vertices, k=n.size))
                    if not any([cand.args == m.args for m in cands]):
                        cands.append(cand)
                edge_insts+=cands

        return [vertices, edge_insts]

    #Used to pretty-print HGraph instances for testing/debugging
    def print(self):

        print(" ".join([m.name for m in self.hgraph[0]]))
        print("---")
        [print(m.name, m.size) for m in {n.edge for n in self.hgraph[1]}]
        print("---")
        for n in self.hgraph[1]:
            print(n.edge.name+" "+" ".join([m.name for m in n.args]))
        print("===")

    #Used to visualize the current hypergraph with graphviz
    #Image gets saved under a folder relative to this file and named according to the current time.
    #Parameter "view" controls whether the generated image should be shown upon generation.
    #Returns the filepath to the generated image.
    def visualize(self, show=False, target_path=None):

        if target_path == None:
            target_path = os.path.dirname(os.path.realpath(__file__))+"\\himages\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')

        view = Gr(format="png", engine="neato")
        view.attr(overlap="false", outputorder="edgesfirst")

        for m in self.hgraph[0]:
            view.node(m.name, substitute(m.name), style="filled", fillcolor="white")
        for i,n in enumerate(self.hgraph[1]):
            view.node(n.edge.name+"_"+str(i), n.edge.name, shape="box", style="filled", fillcolor="white")
            for j,m in enumerate(n.args, 1):
                view.edge(n.edge.name+"_"+str(i), m.name ,taillabel=str(j))

        try:
            view.render(filename=target_path, view=show, cleanup=True)
            return target_path+".png"
        except Exception as e:
            print(e)
            return

    #Used to serialize the graph into text form in the same format it can be parse from.
    #Gets saved under a folder relative to this file and named according to the current time.
    def serialize(self, target_path=None):

        if target_path == None:
            target_path = os.path.dirname(os.path.realpath(__file__))+"\\hgraphs\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')+".txt"

        file = open(target_path, "w")

        file.write("V:")

        file.write("\n"+" ".join([n.name for n in self.hgraph[0]]))

        file.write("\nL:")

        for n in {n.edge for n in self.hgraph[1]}:
            file.write("\n"+n.name+" "+str(n.size))

        file.write("\nE:")

        for n in self.hgraph[1]:
            file.write("\n"+n.edge.name+" "+" ".join([m.name for m in n.args]))

        file.flush()
        file.close()

        return target_path

    #Used to find the core of the hypergraph via a SAT encoding and limboole.
    def _i_limboole(self):

        tempfile = TemporaryFile(mode="w+")

        #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of vertices.
        #At the same time: Impose the "Retaining the identity of element of the core" property of core finding on the mapping of vertices.
        tempfile.write("&\n".join(["("+"|\n".join(["("+"&".join(["!@"+n.name+"@"+l.name for l in self.hgraph[0] if l!=m])+"&@"+n.name+"@"+m.name+"&@"+m.name+"@"+m.name+")" for m in self.hgraph[0]])+")" for n in self.hgraph[0]])+"&\n")

        #This if clause is to prevent generating formulae that are invalid input to limboole, specifically empty brackets "()".
        if len(self.hgraph[1])!=0 and any([n.edge.size != 0 for n in self.hgraph[1]]):

            #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of edges after having filtered the edges by label.
            #In the SAT formula, edges can therefore inherently only be mapped to edges of the same label.
            tempfile.write("&\n".join(["("+"|\n".join(["("+"&".join(["@"+l[0].name+"@"+l[1].name for l in zip(n.args, m.args)])+")" for m in self.hgraph[1] if m.edge == n.edge])+")" for n in self.hgraph[1] if n.edge.size != 0])+"&\n")

        #Only search for retracts whose amount of vertices is stricly smaller that of the original graph.
        #This isn't a direct requirement of retract/cores, but matches which the approach of iteratively looking for retracts instead of the core directly.
        tempfile.write("("+"|\n".join(["("+"&".join(["!@"+m.name+"@"+n.name for m in self.hgraph[0]])+")" for n in self.hgraph[0]])+")")

        tempfile.seek(0)

        result = subprocess.run("limboole -s", stdin=tempfile, stdout=subprocess.PIPE, shell=True)

        tempfile.close()

        return result.returncode, result.stdout.decode()

    #Processes the return of limboole into a retract-morphism and applies this morphism to the current hypergraph.
    def _o_limboole(self, result, am):

        mappings = re.findall(r"@((?:[a-z0-9_.])+)@((?:[a-z0-9_.])+) = 1", result)

        mappings = [n for n in mappings if n[0]!=n[1]]

        lex = {n.name: n for n in self.hgraph[0]}

        mappings = [[lex[n[0]], lex[n[1]]] for n in mappings]

        if am:
            for n in mappings:
                n[1].name += "."+n[0].name
                self.hgraph[0].remove(n[0])
                for m in [l for l in self.hgraph[1]]:
                    if n[0] in m.args:
                        self.hgraph[1].remove(m)
        else:
            for n in mappings:
                self.hgraph[0].remove(n[0])
                for m in [l for l in self.hgraph[1]]:
                    if n[0] in m.args:
                        self.hgraph[1].remove(m)

    #Prompts the iterative search for retracts until the core is found via SAT/limboole.
    #Parameter am controls whether vertices that are not part of the core should have their names attached to the vertices they get mapped to. This may or may not be desired depending on the application.
    def solve(self, am=True):

        #In case the calculation of the core fails, restore the original graph.
        orig = copy.deepcopy(self.hgraph)

        core = False

        #Look for retracts and retracts of those retracts until you can no longer find any. The final retract is a core of the original graph.
        while not core:

            if len(self.hgraph[0])==0 or len(self.hgraph[0])==1:
                core = True
                continue

            returncode, result = self._i_limboole()

            if returncode!=0:
                print("I'm sorry, but CoReS wasn't able to solve your problem.")
                self.graph = orig
                return
            else:
                if result.startswith("% SATISFIABLE"):
                    self._o_limboole(result, am)
                elif result.startswith("% UNSATISFIABLE"):
                    core = True

    #Used to find the core of the hypergraph via a SMT encoding and a python implementation of Z3.
    def _z3(self):

        #The z3py context does not reset inbetween uses, thus we have to manually create a new one for each iteration.
        cntxt = Context()

        s = Solver(ctx=cntxt)

        #Enumeration datatype for vertices. Each vertex gets one element in the datatype.
        var = Datatype("var", ctx=cntxt)

        for n in self.hgraph[0]:
            var.declare(n.name)
        var = var.create()

        vertices = {n: getattr(var, n.name) for n in self.hgraph[0]}

        edge_d_type = {}

        #Record datatypes for edges. Each label "l" has it's own datatype with one constructor which has arr(l) arguments.
        #Labels are considered in that each edges with a certain label is of the datatype that is associated with that label.
        for n in {n.edge for n in self.hgraph[1] if n.edge.size != 0}:

            edge = Datatype(n.name, ctx=cntxt)
            edge.declare("cons_"+n.name, *tuple(("arg_"+str(m), var) for m in range(n.size)))
            edge = edge.create()

            edge_d_type[n] = edge

        edge = {n: {} for n in edge_d_type}

        #Instantiate all edges
        for n in [n for n in self.hgraph[1] if n.edge.size != 0]:

            edge[n.edge][n] = getattr(edge_d_type[n.edge], "cons_"+n.edge.name)(*tuple(vertices[m] for m in n.args))

        var_morph = Function("var_morph", var, var)

        #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of vertices.
        #At the same time: Impose the "Retaining the identity of element of the core" property of core finding on the mapping of vertices.
        s.add(And([Implies(Or([var_morph(vertices[m])==vertices[n] for m in vertices], cntxt), var_morph(vertices[n])==vertices[n]) for n in vertices], cntxt))

        #Only search for retracts whose amount of vertices is stricly smaller that of the original graph.
        #This isn't a direct requirement of retract/cores, but matches which the approach of iteratively looking for retracts instead of the core directly.
        s.add(Not(And([var_morph(vertices[n])==vertices[n] for n in vertices], cntxt)))

        #The morphism of edges to edges is sorted by label, therefore there is an edge-morphism associated with each label.
        for n in edge_d_type:

            func = Function(n.name+"_morph", edge_d_type[n], edge_d_type[n])

            #Impose the morphism property of retracts on the mapping of edges with label "n".
            s.add(And([And([var_morph(getattr(edge_d_type[n], "arg_"+str(l))(edge[n][m])) == getattr(edge_d_type[n], "arg_"+str(l))(func(edge[n][m])) for l in range(n.size)], cntxt) for m in edge[n]], cntxt))

            #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of edges with label "n".
            s.add(And([Or([func(edge[n][m]) == edge[n][k] for k in edge[n]], cntxt) for m in edge[n]], cntxt))

        #Processes the return of z3py into a retract-morphism and applies this morphism to the current hypergraph.
        if s.check() == sat:

            model = s.model()

            r_var = {vertices[k]: k for k in vertices}

            for n in vertices:
                if model.eval(var_morph(vertices[n])!=vertices[n]):

                    tgt = r_var[model.eval(var_morph(vertices[n]))]

                    tgt.name += "."+n.name
                    self.hgraph[0].remove(n)
                    for l in [m for m in self.hgraph[1]]:
                        if n in l.args:
                            self.hgraph[1].remove(l)

            return True

        else:
            return False

    #Prompts the iterative search for retracts until the core is found via SMT/z3py.
    def z3solve(self):

        core = False
        while not core:

            if self._z3():
                continue
            else:
                core=True

#Checks whether each element of an iterable is unique with respect to all other elements of the iterable.
def _unique_list(lst):
    head = set()
    return not any(n in head or head.add(n) for n in lst)

#Used to map the natural numbers + 0 to strings consisting of capital characters starting at P. Used to provide names for labels during generation of hypergraphs.
def _charify(c):

    if c>25:
        return HGraph._charify((c//26)-1)+chr((c%26)+65)
    else:
        return chr(c+65)

#Used to format strings to create certain effects in the python implementation of graphviz.
def substitute(snippet):

    if "_" in snippet:

        tag = "<"

        for n in snippet.split("."):
            x,y = n.split("_")
            if tag != "<":
                tag+="."+x+"<SUB>"+y+"</SUB>"
            else:
                tag+=""+x+"<SUB>"+y+"</SUB>"

        tag+=">"

        return tag
    else:
        return snippet