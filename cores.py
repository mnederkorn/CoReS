import random
import re
import subprocess
import copy
import os
import time

from graphviz import Digraph
from tempfile import TemporaryFile, _TemporaryFileWrapper
from datetime import datetime
from z3 import *

#Objects of class Graph represent a single specific directed graph and the actions you can perform on it.
class Graph:

    #It has to be instantiated by either parsing a graph-structure from a file, copying a preexisting Graph instance or generation a new one according to specified values.
    def __init__(self, **kwargs):

        if not len(kwargs)==1 or not list(kwargs.keys()) <= ["parse", "copy", "gen", ]:
            raise Exception("You have to specify exactly one way to instantiate Graph at a time. Either parse or copy or generate a Graph:\ng = Graph(parse=r\"C:\CoReS\graphs\graph1.txt\")\nh = Graph(copy=g.graph)\ng = Graph(gen=(64,2,1))")
        elif "parse" in kwargs:
            if (isinstance(kwargs["parse"], str) and os.path.isfile(kwargs["parse"])) or isinstance(kwargs["parse"], _TemporaryFileWrapper):
                self.graph = self._parse(kwargs["parse"])
            else:
                raise Exception("The parameter parse has to be an absolute and valid filepath in the form of a string. E.g.: g = Graph(parse=r\"C:\CoReS\graphs\graph1.txt\")")
        elif "copy" in kwargs:
            if isinstance(kwargs["copy"], Graph):
                self.graph = copy.deepcopy(kwargs["copy"].graph)
            else:
                raise Exception("The graph parameter should only be used to copy other preexisting Graph instances. E.g.: h = Graph(copy=g)")
        elif "gen" in kwargs:
            if ((isinstance(kwargs["gen"], tuple) and len(kwargs["gen"])==3) and
                (isinstance(kwargs["gen"][0], int) and kwargs["gen"][0]>0) and
                (isinstance(kwargs["gen"][1], int) and kwargs["gen"][1]>0 and kwargs["gen"][1]<=26) and
                ((isinstance(kwargs["gen"][2], int) or isinstance(kwargs["gen"][2], float)) and kwargs["gen"][2]>=0 and kwargs["gen"][2]<=kwargs["gen"][0]*kwargs["gen"][1])):
                self.graph = self._generate(*kwargs["gen"])
            else:
                raise Exception("The gen parameter has to be of the form of a tuple (nodes_n, labels_n, avg_edges_out) with: int: nodes_n>0, int: 26>=labels_n>0 and float: nodes_n*labels_n>=avg_edges_out>=0. E.g.: g = Graph(gen=(8,2,1))")

    #Deserialize graph from file
    @staticmethod
    def _parse(target):

        if isinstance(target, str):
            data = open(target, "r")
        elif isinstance(target, _TemporaryFileWrapper):
            data = target

        #See if first line fits the specification
        line = data.readline()
        if not re.fullmatch(r"(\d+(\-\d+)*( \d+(\-\d+)*)*|\[[1-9][0-9]*\]) ?(\n)?", line):
            data.close()
            raise Exception("First line has to be of the form:\n(\d+(\-\d+)*( \d+(\-\d+)*)*|\[[1-9][0-9]*\]) ?(\\n)?")
        #Resolve special case of using [x] to refer to vertices 1 to x
        if "[" in line:
            nodes = [str(n) for n in range(1, int(line.rstrip("\n").lstrip("[").rstrip("]"))+1)]
        #If not special case, get list of vertices by splitting first line at whitespace
        else:
            nodes = line.split()
        #Prepare disjunct set of vertices for a following regular expression
        nodes_or = "|".join(nodes)

        #Check for further error of not all vertices being distinct to each other
        for i,n in enumerate(nodes):
            if n in nodes[i+1:len(nodes)]:
                data.close()
                raise Exception("Each node has to be distinct")

        #Create graph under consideration of vertices
        graph = {n: {} for n in nodes}

        #Read in remaining graph (i.e. don't re-parse first line) to get edges
        edges = data.read()

        #Only care for adding edges to graph, if there's lines for edges in the first place
        if len(edges)>0:

            #Whole file has been read, we should now close the file
            data.close()
            #See if all following lines are according to specification
            if not re.fullmatch(r"(("+nodes_or+") ("+nodes_or+") [A-Z] ?\n)*(("+nodes_or+") ("+nodes_or+") [A-Z] ?\n?)?", edges):
                raise Exception("Second to last line have to be in the form of:\n(("+nodes_or+") ("+nodes_or+") [A-Z] ?\\n)*(("+nodes_or+") ("+nodes_or+") [A-Z] ?\\n?)?")
            #Cut off (optional) rightmost \n and split the string into an array of strings with an entry for each edge
            edges = edges.rstrip("\n").split("\n")

            #Check for further error of not all edges being distinct to each other
            for i,n in enumerate(edges):
                if n in edges[i+1:len(edges)]:
                    data.close()
                    raise Exception("Each edge has to be distinct")
            
            #Split each edge into an array of its source vertex, target vertex and label.
            edges = [n.split() for n in edges]

            #Add edges to graph
            for n in edges:
                #If fitting entry in second layer exists, add label
                if n[1] in graph[n[0]]:
                    graph[n[0]][n[1]].add(n[2])
                #Else create second layer entry and add label as first element
                else:
                    graph[n[0]][n[1]] = set(n[2])

        return graph

    #Generating a new Graph
    @staticmethod
    def _generate(nodes_n, labels_n, avg_edges_out):

        #Changing from avg_edges_out to absolute chance of any given edge (V,V,L) to exists
        ratio = avg_edges_out/(nodes_n*labels_n)

        graph = {}

        #First layer with a natural number for each vertex in a dict
        for n in range(nodes_n):
            graph[str(n+1)] = {}
            #Second layer with a natural number for a vertex in a dict if there is an edge from the corresponding vertex in the first layer to this one
            #Only gets created once an edge happens to be generated
            for m in range(nodes_n):
                #Third layer with a character for a label in a set if the edge happens to be generated
                for l in range(labels_n):
                    #If edge is generated:
                    if(random.random()<ratio):
                        #Add label to set
                        if str(m+1) in graph[str(n+1)]:
                            graph[str(n+1)][str(m+1)].add(chr(l+65))
                        #Or create set with label as first element if edge n->m was empty so far
                        else:
                            graph[str(n+1)][str(m+1)] = set(chr(l+65))

        return graph

    #Print graph to console
    def print(self, length, style):

        #Print length of graph yes/no
        if length==1:
            print("["+str(len(self.graph))+"]")

        #Print graph itself like python prints dicts
        if style==1:
            print(self.graph)
        #Print graph more pretty, but also more verbose
        elif style == 2:
            for n in self.graph:
                src = n
                for m in self.graph[n]:
                    tgt = " ("+m
                    for l in self.graph[n][m]:
                        tgt += " "+l
                    tgt += ")"
                    src += tgt
                print(src)

    #Visualize graph object with Graphviz
    def visualize(self, target_path=None):
        #Digraph, node, edge and render are graphviz functions

        #If no path given, use time dependant file placed relative to this file
        if target_path == None:
            target_path = os.path.dirname(os.path.realpath(__file__))+"\\images\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')

        view = Digraph(format="png")

        #Add all nodes and edges to visualization
        for n in self.graph:
            view.node(n)
            for m in self.graph[n]:
                label = ""
                for l in sorted(self.graph[n][m]):
                    label += l
                view.edge(n,m,label)
        try:
            #Try to render at target_path+".png" (because Digraph(format="png")) and delete intermediate file used by graphviz at target_path (cleanup=True)
            view.render(filename=target_path, view=False, cleanup=True)
            return target_path+".png"
        except Exception as e:
            print(e)
            return

    #Serialize graph object
    def serialize(self, target_path=None):

        #If no path given, use time dependant file placed relative to this file
        if target_path == None:
            target_path = os.path.dirname(os.path.realpath(__file__))+"\\graphs\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')+".txt"

        file = open(target_path, "w")

        #Write all vertices to first line
        for n in self.graph:
            file.write(n+" ")

        file.write("\n")

        #Write all edges-tuples to the following lines
        for n,m,l in [(n,m,l) for n in self.graph for m in self.graph[n] for l in self.graph[n][m]]:
            file.write(n+" "+m+" "+l+"\n")

        file.close()

        return target_path

    #Reduce the graph object as instructed by the result of a solver
    def _reduce(self, mappings):

        #We take in the mapping for each vertex, but only need to actually handle those don't map to themselves
        mappings = [n for n in mappings if n[0]!=n[1]]

        #Change remaining mappings such that mappings like [['1', '2'], ['3', '2']] become [['1', '2'], ['3', '2-1']] to combat the graph object vertices namings not being invariant during it's reduction
        #['1', '2'] changes vertex '2' to be '2-1', thus the mapping ['3', '2'] wouldn't know a vertex '2' anymore, requiring its change to ['3', '2-1']
        mappings = [[n[0]+"".join(["-"+m[0] for m in mappings[:i] if m[1] == n[0]]),n[1]+"".join(["-"+m[0] for m in mappings[:i] if m[1] == n[1]])] for i,n in enumerate(mappings)]

        #Apply the mapping
        for n in mappings:

            #Delete a to-be reduced vertex
            del self.graph[n[0]]
            #And attach it's name to the vertex it gets mapped to
            #Instead of renaming the vertex it gets mapped to, we need to remove (with pop) and reassign it's values to a fittingly named new vertex
            self.graph[n[1]+"-"+n[0]] = self.graph.pop(n[1])

            for m in self.graph:

                #Delete a to-be reduced vertex in the same way as vertices
                if n[0] in self.graph[m]:
                    del self.graph[m][n[0]]
                if n[1] in self.graph[m]:
                    self.graph[m][n[1]+"-"+n[0]] = self.graph[m].pop(n[1])

    #Promt limboole for Retract search
    def _i_limboole(self):

        #Write SAT formula into temporary file
        tempfile = TemporaryFile(mode="w+")

        tempfile.write("&\n".join(["("+"|\n".join(["("+"&".join(["!.@{}_@{}".format(str(n),str(l)) for l in self.graph if l!=m])+"&.@{}_@{}&.@{}_@{})".format(str(n),str(m),str(m),str(m)) for m in self.graph])+")" for n in self.graph])+"&\n")        

        edges = [[n,m] for n in self.graph for m in self.graph[n]]

        for n in edges:
            edges_group = [m for m in edges if (self.graph[m[0]][m[1]] >= self.graph[n[0]][n[1]])]
            tempfile.write("("+"|".join(["(.@{}_@{}&.@{}_@{})".format(n[0],l[0],n[1],l[1]) for l in edges_group])+")&\n")

        tempfile.write("("+"|\n".join(["("+"&".join(["!.@{}_@{}".format(str(m),str(n)) for m in self.graph])+")" for n in self.graph])+")")

        #For limboole to be able to read the tempfile properly, we have to reset it's seeker
        tempfile.seek(0)

        #Prompt limboole with the generated formula and return the result with a PIPE
        result = subprocess.run("limboole -s", stdin=tempfile, stdout=subprocess.PIPE, shell=True)

        #Close tempfile
        tempfile.close()

        #Return returncode and the result-string (after turning it from bytecode to string)
        return result.returncode, result.stdout.decode()

    #Turn limboole result into a mapping
    def _o_limboole(self, result):

        #Take all limboole-result assignments and only keep those that actually happen (i.e. = 1)
        mappings = re.findall(r".(@\d+(?:-\d+)*_@\d+(?:-\d+)*) = 1\r\n", result)

        #Format them from limboole output to our required format
        mappings = [[m.lstrip("@") for m in n.split("_")] for n in mappings]

        self._reduce(mappings)

    #Reduce graph object to it's core via limboole
    def solve(self):

        #Copy original in case limboole fails during an iteration
        orig = copy.deepcopy(self.graph)

        core = False

        #Iterate over "finding smaller retract" until we find core
        while not core:

            #SAT formula only works for more than two vertices, but one vertex is always a core
            if (len(self.graph)==1):
                core = True
                continue

            #Prompt limboole with our formula, see _i_limboole
            returncode, result = self._i_limboole()

            #returncode!=0 if limboole crashed
            if returncode!=0:
                print("I'm sorry, but CoReS wasn't able to solve your problem.")
                self.graph = orig
                return
            #Check whether Graph could be reduced further
            else:
                #If it could, reiterate
                if result.startswith("% SATISFIABLE"):
                    self._o_limboole(result)
                #If it couldn't, end search
                elif result.startswith("% UNSATISFIABLE"):
                    core = True

    #Used to find the core of the graph via a SMT encoding and a python implementation of Z3.
    def _z3(self):

        #The z3py context does not reset inbetween uses, thus we have to manually create a new one for each iteration.
        cntxt = Context()

        s = Solver(ctx=cntxt)

        #Enumeration datatype for vertices. Each vertex gets one element in the datatype.
        var = Datatype("var", ctx=cntxt)

        for n in self.graph:
            var.declare(str(n))
        var = var.create()

        vertices = {n: getattr(var, str(n)) for n in self.graph}

        edge_d_type = {}

        #Record datatypes for edges. Each label "l" has it's own datatype with one constructor which has arguments for accessing the source and target node.
        #Labels are considered in that each edges with a certain label is of the datatype that is associated with that label.
        for n in {l for n in self.graph for m in self.graph[n] for l in self.graph[n][m]}:

            edge = Datatype(n, ctx=cntxt)
            edge.declare("cons_"+n, ("src", var), ("tgt", var))
            edge = edge.create()

            edge_d_type[n] = edge

        edge = {n: [] for n in edge_d_type}

        #Instantiate all edges
        for n,m,l in [(n,m,l) for n in self.graph for m in self.graph[n] for l in self.graph[n][m]]:

            edge[l].append(getattr(edge_d_type[l], "cons_"+l)(vertices[n], vertices[m]))

        var_morph = Function("var_morph", var, var)

        #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of vertices.
        #At the same time: Impose the "Retaining the identity of element of the core" property of core finding on the mapping of vertices.
        s.add(And([Implies(Or([var_morph(vertices[m])==vertices[n] for m in vertices], cntxt), var_morph(vertices[n])==vertices[n]) for n in vertices], cntxt))

        #Only search for retracts whose amount of vertices is stricly smaller that of the original graph.
        #This isn't a direct requirement of retract/cores, but matches which the approach of iteratively looking for retracts instead of the core directly.
        s.add(Not(And([var_morph(vertices[n])==vertices[n] for n in vertices], cntxt)))

        #The morphism of edges to edges is sorted by label, therefore there is an edge-morphism associated with each label.
        for n in edge_d_type:

            edge_morph = Function(n+"_morph", edge_d_type[n], edge_d_type[n])

            #Impose the morphism property of retracts on the mapping of edges with label "n".
            s.add(And([And(var_morph(edge_d_type[n].src(m)) == edge_d_type[n].src(edge_morph(m)), var_morph(edge_d_type[n].tgt(m)) == edge_d_type[n].tgt(edge_morph(m)), cntxt) for m in edge[n]], cntxt))

            #Impose the "Map each element of the domain to exactly one element of the codomain" property of functions on the mapping of edges with label "n".
            s.add(And([Or([edge_morph(m) == k for k in edge[n]], cntxt) for m in edge[n]], cntxt))

        #Processes the return of z3py into a retract-morphism and applies this morphism to the current graph.
        if s.check() == sat:

            model = s.model()

            r_var = {vertices[k]: k for k in vertices}

            mappings = []

            for n in vertices:
                if model.eval(var_morph(vertices[n])!=vertices[n]):
                    mappings.append([n, r_var[model.eval(var_morph(vertices[n]))]])

            self._reduce(mappings)                        

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