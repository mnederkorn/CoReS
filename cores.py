import random
import re
import subprocess
import copy
import os

from graphviz import Digraph
from tempfile import TemporaryFile
from datetime import datetime
from z3 import *

class Graph:

	#Instantiating a graph Object
	def __init__(self, parse=None, graph=None, gen=None):

		#Exactly one parameter has to be given and that one parameter has to conform to specs

		if parse == None and graph == None and gen == None:
			raise Exception("You have to parse, copy or generate a Graph.")
		elif ((parse != None and graph != None) or (parse != None and gen != None) or (graph != None and gen != None)):
			raise Exception("You have to parse OR copy OR generate a Graph.")
		elif parse != None:
			if isinstance(parse, str):
				self.graph = self._parse_file(parse)
			else:
				raise Exception("""The parameter parse has to be a absolute filepath in the form of a string. E.g.:
new_graph = Graph(parse=r\"C:\\yourgraph.txt\") or
new_graph = Graph(parse=\"C:\\\\yourgraph.txt\")""")
		elif graph != None:
			if ((isinstance(graph, dict) and len(graph)>0) and
				all(isinstance(graph[n], dict) and (re.fullmatch(r"\d+(\-\d+)*", n)) for n in graph) and
				all((m in graph) and (isinstance(graph[n][m], set) and len(m)>0) for n in graph for m in graph[n]) and
				all((isinstance(k, str) and re.fullmatch(r"[A-Z]", k)) for n in graph for m in graph[n] for l in graph[n][m] for k in l)):
				self.graph = copy.deepcopy(graph)
			else:
				raise Exception("""The graph parameter should only be used to copy other preexisting Graphs. E.g.:
new_graph = Graph(graph=YourGraphInstance.graph)""")
		elif gen != None:
			if ((isinstance(gen, tuple) and len(gen)==3) and
				(isinstance(gen[0], int) and gen[0]>0) and
				(isinstance(gen[1], int) and gen[1]>0 and gen[1]<=26) and
				((isinstance(gen[2], int) or isinstance(gen[2], float)) and gen[2]>=0 and gen[2]<=gen[0]*gen[1])):
				self.graph = self._generate(*gen)
			else:
				raise Exception("""The gen parameter has to be of the form of a tuple (nodes_n, labels_n, avg_edges_out) with:
int: nodes_n>0 representing the desired amount of nodes,
int: 26>=labels_n>0 representing the desired amount of labels and
float: nodes_n*labels_n>=avg_edges_out>=0 representing the desired approximate average amount of edges leaving each node. G.g.:
new_graph = Graph(gen=(8,2,1.1))""")


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

	#Read in file to parse, if successful, kick off parsing and return resulting graph
	@staticmethod
	def _parse_file(target_path):

		data = open(target_path, "r")

		return Graph._parse(data)

	#Deserialize graph from file
	@staticmethod
	def _parse(data):

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

		try:
			file = open(target_path, "w")
		except Exception as e:
			print(e)
			return

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

		#Each vertex
		for n in self.graph:
			tempfile.write("(\n")
			#gets mappend to a vertex
			for i,m in enumerate(self.graph):
				tempfile.write("\t(")
				#and does not get mapped to all other vertices
				for j,l in enumerate(self.graph):
					if not m==l:
						tempfile.write("!.@"+str(n)+"_@"+str(l))
					else:
						tempfile.write(".@"+str(n)+"_@"+str(l))
					tempfile.write(" & ")
				if not i+1 == len(self.graph):
					tempfile.write(".@"+str(m)+"_@"+str(m)+") |\n")
				else:
					tempfile.write(".@"+str(m)+"_@"+str(m)+")\n")
			tempfile.write(")\n&\n")

		#Create a list of edges (summarizing labels) from the graph
		edges = [[n,m] for n in self.graph for m in self.graph[n]]
		#For each edge-bundle
		for n in edges:
			tempfile.write("(\n")
			#Create list of all edge-bundles whose set of labels is a superset of the set of labels of bundle n
			edges_group = [m for m in edges if (self.graph[m[0]][m[1]] >= self.graph[n[0]][n[1]])]
			#Map bundle n to a superset-bundle
			for i,m in enumerate(edges_group):
				tempfile.write("\t(.@"+n[0]+"_@"+m[0]+" & .@"+n[1]+"_@"+m[1]+")")
				if not i+1 == len(edges_group):
					tempfile.write(" |\n")
			tempfile.write("\n)\n&\n")

		tempfile.write("(\n")
		#Out of all vertices
		for i,n in enumerate(self.graph):
			tempfile.write("\t(")
			#One vertex cannot map to iself
			for j,m in enumerate(self.graph):
				tempfile.write("!.@"+m+"_@"+n)
				if not j+1 == len(self.graph):
					tempfile.write(" & ")
			if not i+1 == len(self.graph):
				tempfile.write(") |\n")
		tempfile.write(")\n)")

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

	#Promt Z3 for Retract search
	def _z3(self):

		#Needs new context for each iteration, since Z3 API context doesn't reset inbetween uses/iterations
		c = Context()

		#Create a list of edges from graph
		edges = list(enumerate([(n,m,l) for n in self.graph for m in self.graph[n] for l in self.graph[n][m]]))

		#Create a list of a set of labels from graph
		labels = list(enumerate({n for m in [self.graph[n][m] for n in self.graph for m in self.graph[n]] for n in m}))


		#Create datatypes for vertices
		V = Datatype("V",ctx=c)
		#Create datatypes for edges and labels, if edges exist
		if not len(edges) == 0:
			E = Datatype("E",ctx=c)
			L = Datatype("L",ctx=c)

		vertices = {}

		#Instantiate vertices and save them in vertices for later use
		for n in enumerate(self.graph):
			V.declare("V"+n[1])
			vertices[n[1]] = n[0]
		V = V.create()

		#Instantiate edges and labels if edges exist and save labels for later use
		if not len(edges) == 0:
			for n in edges:
				E.declare("E"+str(n[0]))
			E = E.create()

			labels_2 = {}

			for n in labels:
				L.declare("L"+n[1])
				labels_2[n[1]] = n[0]
			L = L.create()

		#Declare src, tgt and lab functions
		if not len(edges) == 0:
			src = Function("src", E, V)
			tgt = Function("tgt", E, V)
			lab = Function("lab", E, L)

		s = Solver(ctx=c)

		#Define edge assignments
		for n in edges:
			s.add(src(E.constructor(n[0])())==V.constructor(vertices[n[1][0]])())
			s.add(tgt(E.constructor(n[0])())==V.constructor(vertices[n[1][1]])())
			s.add(lab(E.constructor(n[0])())==L.constructor(labels_2[n[1][2]])())

		#Declare vertex morphism
		vmorph = Function("vmorph", V, V)
		if not len(edges) == 0:
			#Declare edge morphism
			emorph = Function("emorph", E, E)

			e = Const("e", E)

			#Add assertions for the morphism to be a homomorphism
			s.add(ForAll(e, (src(emorph(e))==vmorph(src(e)))))
			s.add(ForAll(e, (tgt(emorph(e))==vmorph(tgt(e)))))
			s.add(ForAll(e, (lab(emorph(e))==lab(e))))

		v1, v2 = Consts("v1 v2", V)
		#Add assertion that not every vertex can be mapped to
		s.add(Exists(v1, (Not (Exists (v2, (v1==vmorph(v2)))))))
		#Add assertions that vertices of the image of the homomorphism must be mapped identically
		s.add(ForAll(v1, (Implies ((Exists (v2, v1==vmorph(v2))),(v1==vmorph(v1))))))

		mappings = []

		#Get model from constrains
		if s.check() == sat:
			#If there exists a fitting retract, extract mappings from model and create mappings
			m = s.model()
			for n in vertices:
				if ("V"+n != str(m.eval(vmorph(V.constructor(vertices[n])())))):
					mappings.append([n, str(m.eval(vmorph(V.constructor(vertices[n])()))).lstrip("V")])
		else:
			return False

		#Prompt reduction of graph object
		self._reduce(mappings)

		#Signal sucessfull reduction
		return True

	#Reduce graph object to it's core via Z3
	def z3solve(self):

		core = False

		#Iterate over "finding smaller retract" until we find core
		while not core:

			# Prompt Z3 with our formula, reduce (included in _z3) and repeat if successfull
			if self._z3():
				continue
			else:
				core = True