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

	def __init__(self, parse=None, graph=None, gen=None):

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

	@staticmethod
	def _generate(nodes_n, labels_n, avg_edges_out):

		ratio = avg_edges_out/(nodes_n*labels_n)

		graph = {}

		for n in range(nodes_n):
			graph[str(n+1)] = {}
			for m in range(nodes_n):
				for l in range(labels_n):
					if(random.random()<ratio):
						if str(m+1) in graph[str(n+1)]:
							graph[str(n+1)][str(m+1)].add(chr(l+65))
						else:
							graph[str(n+1)][str(m+1)] = set(chr(l+65))

		return graph

	@staticmethod
	def _parse_file(target_path):

		try:
			data = open(target_path, "r")
		except Exception as e:
			print(e)
			return

		return Graph._parse(data)		

	@staticmethod
	def _parse(data):

		line = data.readline()
		if not re.fullmatch(r"(\d+(\-\d+)*( \d+(\-\d+)*)*|\[[1-9][0-9]*\]) ?(\n)?", line):
			data.close()
			raise Exception("First line has to be of the form:\n(\d+(\-\d+)*( \d+(\-\d+)*)*|\[[1-9][0-9]*\]) ?(\\n)?")
		if "[" in line:
			nodes = [str(n) for n in range(1, int(line.rstrip("\n").lstrip("[").rstrip("]"))+1)]
		else:
			nodes = line.split()
		nodes_or = "|".join(nodes)

		for i,n in enumerate(nodes):
			if n in nodes[i+1:len(nodes)]:
				data.close()
				raise Exception("Each node has to be distinct")

		graph = {n: {} for n in nodes}

		edges = data.read()

		if len(edges)>0:

			data.close()
			if not re.fullmatch(r"(("+nodes_or+") ("+nodes_or+") [A-Z] ?\n)*(("+nodes_or+") ("+nodes_or+") [A-Z] ?\n?)?", edges):
				raise Exception("Second to last line have to be in the form of:\n(("+nodes_or+") ("+nodes_or+") [A-Z] ?\\n)*(("+nodes_or+") ("+nodes_or+") [A-Z] ?\\n?)?")
			edges = edges.rstrip("\n").split("\n")

			for i,n in enumerate(edges):
				if n in edges[i+1:len(edges)]:
					data.close()
					raise Exception("Each edge has to be distinct")
					
			edges = [n.split() for n in edges]

			for n in edges:
				if n[1] in graph[n[0]]:
					graph[n[0]][n[1]].add(n[2])
				else:
					graph[n[0]][n[1]] = set(n[2])

		return graph

	def print(self, length, style):

		if length==1:
			print("["+str(len(self.graph))+"]")

		if style==1:
			print(self.graph)
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

	def visualize(self, target_path=None):

		if target_path == None:
			target_path = os.path.dirname(os.path.realpath(__file__))+"\\images\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')

		view = Digraph(format="png")

		for n in self.graph:
			view.node(n)
			for m in self.graph[n]:
				label = ""
				for l in sorted(self.graph[n][m]):
					label += l
				view.edge(n,m,label)

		try:
			view.render(filename=target_path, view=False, cleanup=True)
			return target_path
		except Exception as e:
			print(e)
			return

	def serialize(self, target_path=None):

		if target_path == None:
			target_path = os.path.dirname(os.path.realpath(__file__))+r"\\graphs\\"+datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')+".txt"

		try:
			file = open(target_path, "w")
		except Exception as e:
			print(e)
			return

		for n in self.graph:
			file.write(n+" ")

		file.write("\n")

		for n,m,l in [(n,m,l) for n in self.graph for m in self.graph[n] for l in self.graph[n][m]]:
			file.write(n+" "+m+" "+l+"\n")

		file.close()
		return target_path

	def _reduce(self, mappings):

		mappings = [n for n in mappings if n[0]!=n[1]]

		mappings = [[n[0]+"".join(["-"+m[0] for m in mappings[:i] if m[1] == n[0]]),n[1]+"".join(["-"+m[0] for m in mappings[:i] if m[1] == n[1]])] for i,n in enumerate(mappings)]

		for n in mappings:

			del self.graph[n[0]]
			self.graph[n[1]+"-"+n[0]] = self.graph.pop(n[1])

			for m in self.graph:

				if n[0] in self.graph[m]:
					del self.graph[m][n[0]]
				if n[1] in self.graph[m]:
					self.graph[m][n[1]+"-"+n[0]] = self.graph[m].pop(n[1])

	def _i_limboole(self):

		tempfile = TemporaryFile(mode="w+")

		for n in self.graph:
			tempfile.write("(\n")
			for i,m in enumerate(self.graph):
				tempfile.write("\t(")
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

		edges = [[n,m] for n in self.graph for m in self.graph[n]]
		for n in edges:
			tempfile.write("(\n")
			edges_group = [m for m in edges if (self.graph[m[0]][m[1]] >= self.graph[n[0]][n[1]])]
			for i,m in enumerate(edges_group):
				tempfile.write("\t(.@"+n[0]+"_@"+m[0]+" & .@"+n[1]+"_@"+m[1]+")")
				if not i+1 == len(edges_group):
					tempfile.write(" |\n")
			tempfile.write("\n)\n&\n")

		tempfile.write("(\n")
		for i,n in enumerate(self.graph):
			tempfile.write("\t(")
			for j,m in enumerate(self.graph):
				tempfile.write("!.@"+m+"_@"+n)
				if not j+1 == len(self.graph):
					tempfile.write(" & ")
			if not i+1 == len(self.graph):
				tempfile.write(") |\n")
		tempfile.write(")\n)")

		tempfile.seek(0)

		result = subprocess.run("limboole -s", stdin=tempfile, stdout=subprocess.PIPE, shell=True)

		tempfile.close()

		return result.returncode, result.stdout.decode()

	def _o_limboole(self, result):

		mappings = re.findall(r".(@\d+(?:-\d+)*_@\d+(?:-\d+)*) = 1\r\n", result)

		mappings = [[m.lstrip("@") for m in n.split("_")] for n in mappings]

		self._reduce(mappings)

	def solve(self):

		orig = copy.deepcopy(self.graph)

		core = False

		while not core:

			if (len(self.graph)==1):
				core = True
				continue

			returncode, result = self._i_limboole()

			if returncode!=0:
				print("I'm sorry, but CoReS wasn't able to solve your problem.")
				self.graph = orig
				return
			else:
				if result.startswith("% SATISFIABLE"):
					self._o_limboole(result)
				elif result.startswith("% UNSATISFIABLE"):
					core = True

	def _z3(self):

		c = Context()

		edges = list(enumerate([(n,m,l) for n in self.graph for m in self.graph[n] for l in self.graph[n][m]]))

		labels = list(enumerate({n for m in [self.graph[n][m] for n in self.graph for m in self.graph[n]] for n in m}))

		V = Datatype("V",ctx=c)
		if not len(edges) == 0:
			E = Datatype("E",ctx=c)
			L = Datatype("L",ctx=c)

		vertices = {}

		for n in enumerate(self.graph):
			V.declare("V"+n[1])
			vertices[n[1]] = n[0]
		V = V.create()

		if not len(edges) == 0:
			for n in edges:
				E.declare("E"+str(n[0]))
			E = E.create()

			labels_2 = {}

			for n in labels:
				L.declare("L"+n[1])
				labels_2[n[1]] = n[0]
			L = L.create()


		if not len(edges) == 0:
			src = Function("src", E, V)
			tgt = Function("tgt", E, V)
			lab = Function("lab", E, L)

		s = Solver(ctx=c)

		for n in edges:
			s.add(src(E.constructor(n[0])())==V.constructor(vertices[n[1][0]])())
			s.add(tgt(E.constructor(n[0])())==V.constructor(vertices[n[1][1]])())
			s.add(lab(E.constructor(n[0])())==L.constructor(labels_2[n[1][2]])())

		vmorph = Function("vmorph", V, V)
		if not len(edges) == 0:
			emorph = Function("emorph", E, E)

			e = Const("e", E)

			s.add(ForAll(e, (src(emorph(e))==vmorph(src(e)))))
			s.add(ForAll(e, (tgt(emorph(e))==vmorph(tgt(e)))))
			s.add(ForAll(e, (lab(emorph(e))==lab(e))))

		v1, v2 = Consts("v1 v2", V)
		s.add(Exists(v1, (Not (Exists (v2, (v1==vmorph(v2)))))))
		s.add(ForAll(v1, (Implies ((Exists (v2, v1==vmorph(v2))),(v1==vmorph(v1))))))

		if not len(edges) == 0:
			e1, e2 = Consts("e1 e2", E)

			s.add(ForAll(e1, (Implies ((Exists (e2, e1==emorph(e2))),(e1==emorph(e1))))))

		mappings = []

		if s.check() == sat:
			m = s.model()
			for n in vertices:
				if ("V"+n != str(m.eval(vmorph(V.constructor(vertices[n])())))):
					mappings.append([n, str(m.eval(vmorph(V.constructor(vertices[n])()))).lstrip("V")])
		else:
			return False

		self._reduce(mappings)

		return True

	def z3solve(self):

		core = False

		while not core:

			if self._z3():
				continue
			else:
				core = True