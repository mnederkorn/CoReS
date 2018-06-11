import os
import copy

from cores import Graph as graph
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
from tempfile import TemporaryFile

zoom_factor = (2**(1/2))

class Gui:

	def __init__(self):

		self.top = Tk()

		self.menubar = Menu(self.top)
		self.filemenu = Menu(self.menubar, tearoff=0)
		self.newmenu = Menu(self.filemenu, tearoff=0)
		self.newmenu.add_command(label="Empty", command=self.new_empty, accelerator="Ctrl-N")
		self.newmenu.add_command(label="Generate", command=self.new_generate, accelerator="Ctrl-G")
		self.filemenu.add_cascade(label="New", menu=self.newmenu)
		self.filemenu.add_command(label="Open", command=self.open_file, accelerator="Ctrl-O")
		self.filemenu.add_command(label="Save", command=self.save_file, accelerator="Ctrl-S")
		self.filemenu.add_command(label="Save as", command=self.save_file_as, accelerator="Ctrl-Shift-S")
		self.menubar.add_cascade(label="File", menu=self.filemenu)
		self.top.config(menu=self.menubar)

		self.frame_left = Frame(self.top)
		self.button_frame = Frame(self.frame_left)
		self.render_btn = Button(master=self.button_frame, command=self.render, text="Render")
		self.core_btn = Button(master=self.button_frame, command=self.get_core, text="Get Core")
		self.text = Text(master=self.frame_left, width=30, height=20, wrap=NONE, undo=True)
		self.scrollx = Scrollbar(master=self.frame_left, command=self.text.xview, orient=HORIZONTAL)
		self.scrolly = Scrollbar(master=self.frame_left, command=self.text.yview, orient=VERTICAL)
		self.text.config(xscrollcommand=self.scrollx.set, yscrollcommand=self.scrolly.set)

		self.canvas = Canvas(master=self.top)
		self.canvas.config(width=400)

		self.render_btn.pack(side=LEFT, fill=X, expand=True)
		self.core_btn.pack(side=RIGHT, fill=X, expand=True)
		self.button_frame.grid(row=1, column=1, sticky="we")
		self.text.grid(row=2, column=1, sticky="ns")
		self.scrollx.grid(row=3, column=1, sticky="we")
		self.scrolly.grid(row=2, column=2, sticky="ns")
		self.frame_left.rowconfigure(2, weight=1)
		
		self.frame_left.pack(side=LEFT, fill=Y, expand=False)

		self.canvas.pack(side=RIGHT, fill=BOTH, expand=True)
		self.canvas.update()

		self.canvas.bind("<ButtonPress-1>", self.scroll_start)
		self.canvas.bind("<B1-Motion>", self.scroll_move)
		self.canvas.bind("<MouseWheel>",self.zoom)
		self.top.bind_all("<Control-Key-n>", self.new_empty)
		self.top.bind_all("<Control-Key-g>", self.new_generate)
		self.top.bind_all("<Control-Key-o>", self.open_file)
		self.top.bind_all("<Control-Key-s>", self.save_file)
		self.top.bind_all("<Control-Key-S>", self.save_file_as)
		self.top.bind_all("<Control-Key-r>", self.render)
		self.top.bind_all("<Control-Key-c>", self.get_core)
		self.top.bind_all("<Control-Key-C>", self.get_core)

		self.new_empty()

		self.top.mainloop()

	def title(self):

		if not self.file:
			self.top.title("tmp - CoReS")
		else:
			self.top.title(self.file+" - CoReS")

	def to_text(self):

		self.text.delete(1.0,END)

		if not self.graph == None:

			for n in self.graph.graph:
				self.text.insert(END, n+" ")

			for (n,m,l) in [(n,m,l) for n in self.graph.graph for m in self.graph.graph[n] for l in self.graph.graph[n][m]]:
				self.text.insert(END, "\n"+n+" "+m+" "+l)

	def from_text(self):

		tempfile = TemporaryFile(mode="w+")
		tempfile.write(self.text.get("1.0",'end-1c'))
		tempfile.seek(0)
		try:
			self.graph = graph(graph=graph._parse(tempfile))
		except Exception as e:
			messagebox.showerror("Error",e)
			return False
		tempfile.close()
		return True

	def render(self, *_):

		if self.from_text():
			tmp = self.graph.visualize()
			self.img = Image.open(tmp)
			self.re_render()
		else:
			return

	def re_render(self):

		self.img_cache=self.img.resize((int(self.img.size[0]*self.scale),int(self.img.size[1]*self.scale)),Image.ANTIALIAS)
		self.pi = ImageTk.PhotoImage(self.img_cache)
		self.canvas.delete("all")
		self.canvas.create_image(0, 0, anchor="nw", image=self.pi)
		self.canvas.config(scrollregion=self.canvas.bbox("all"))

		if self.scale >= 1:
			self.canvas.config(width=max(self.top.winfo_screenwidth()/4,min(self.img_cache.width, self.top.winfo_screenwidth()/2**(1/2))), height=min(self.img_cache.height, self.top.winfo_screenheight()/2**(1/2)))

	def get_core(self, e):

		if self.from_text():

			old = copy.deepcopy(self.img)

			l = Label(master=self.top, text="Searching for Core...", background="orange", font=("TkDefaultFont",24))

			l.place(x=0,y=0)

			self.top.update()

			w,h = int(l.winfo_width()/2),int(l.winfo_height()/2)

			l.place(relx=0.5, rely=0.5, x=-w, y=-h)

			self.top.update()

			if (e.keysym == "c"):
				self.graph.solve()
			elif (e.keysym == "C"):
				self.graph.z3solve()

			l.destroy()

			self.to_text()
			self.render()

			OldGui(old)

		else:
			return

	def new_empty(self, *_):

		self.file = None
		self.graph = None
		self.title()
		self.to_text()
		self.scale=1.0
		self.canvas.delete("all")

	def generate(self, nodes_n,labels_n,avg_out):

		self.file = None
		self.graph = graph(gen=(nodes_n,labels_n,avg_out))
		self.title()
		self.to_text()
		self.scale=1.0
		self.render()

	def new_generate(self,*_):

		top = Toplevel()
		top.resizable(False, False)
		top.title("Generate Graph")
		nodes_lab = Label(top, text="Nodes #")
		nodes_n = Spinbox(top, from_=1, to=sys.maxsize)
		nodes_n.delete(0, 1)
		nodes_n.insert(0, 8)
		labels_lab = Label(top, text="Labels #", anchor="w")
		labels_n = Spinbox(top, from_=1, to=sys.maxsize)
		labels_n.delete(0, 1)
		labels_n.insert(0, 2)
		out_lab = Label(top, text="Avg. Edges per Node   ", anchor="w")
		avg_out = Spinbox(top, from_=0, to=sys.maxsize, increment=0.05)
		avg_out.delete(0, 4)
		avg_out.insert(0, 1.1)
		button = Button(top, text="Generate", command=lambda: [self.generate(int(nodes_n.get()),int(labels_n.get()),float(avg_out.get())), top.destroy()])

		nodes_lab.grid(row=1,column=1,sticky="w")
		labels_lab.grid(row=2,column=1,sticky="w")
		out_lab.grid(row=3,column=1,sticky="w")
		nodes_n.grid(row=1,column=2)
		labels_n.grid(row=2,column=2)
		avg_out.grid(row=3,column=2)
		button.grid(row=4,column=1,columnspan=2,sticky="we")

		button.bind("<Return>", lambda _: [self.generate(int(nodes_n.get()),int(labels_n.get()),float(avg_out.get())), top.destroy()])

		button.focus()

		top.mainloop()

	def open_file(self, *_):

		file = filedialog.askopenfilename(parent=self.top, initialdir=os.path.dirname(os.path.realpath(__file__)), filetypes=[("Plain Text", ".txt"),("All Files", ".*")])

		if file:
			self.file=file
			self.graph = graph(parse=file)
			self.title()
			self.to_text()
			self.scale=1.0
			self.render()

	def save_file(self, *_):

		if self.file:
			if self.from_text():
				self.graph.serialize(self.file)
				self.title()
				self.render()
			else:
				return
		else:
			self.save_file_as()

	def save_file_as(self, *_):

		if self.graph == None:
			messagebox.showwarning("Attention","You can't save an empty graph.")
			return

		self.file = filedialog.asksaveasfilename(parent=self.top, initialdir=os.path.dirname(os.path.realpath(__file__)), filetypes=[("Plain Text", ".txt"),("All Files",".*")], defaultextension=".txt")
		if self.file:
			if self.from_text():
				self.graph.serialize(self.file)
				self.title()
				self.render()
			else:
				return

	def scroll_start(self, event):
	    self.canvas.scan_mark(event.x, event.y)

	def scroll_move(self, event):
	    self.canvas.scan_dragto(event.x, event.y, gain=1)

	def zoom(self, e):

		if (zoom_factor**-4)<=self.scale*(zoom_factor**(e.delta/120))<=(zoom_factor**2):
			self.scale*=(zoom_factor**(e.delta/120))
			self.re_render()

class OldGui:

	def __init__(self, img):

		self.old = Toplevel()
		self.old.title("Original Graph")
		self.canvas = Canvas(master=self.old)
		self.scale = 1.0
		self.img = img

		self.canvas.bind("<ButtonPress-1>", self.scroll_start)
		self.canvas.bind("<B1-Motion>", self.scroll_move)
		self.canvas.bind("<MouseWheel>",self.zoom)

		self.canvas.pack(fill=BOTH, expand=True)

		self.re_render()

		self.old.mainloop()


	def scroll_start(self, event):
		self.canvas.scan_mark(event.x, event.y)

	def scroll_move(self, event):
		self.canvas.scan_dragto(event.x, event.y, gain=1)

	def zoom(self, e):
		if (zoom_factor**-4)<=self.scale*(zoom_factor**(e.delta/120))<=(zoom_factor**2):
			self.scale*=(zoom_factor**(e.delta/120))
			self.re_render()

	def re_render(self):

		self.img_cache=self.img.resize((int(self.img.size[0]*self.scale),int(self.img.size[1]*self.scale)),Image.ANTIALIAS)
		self.pi = ImageTk.PhotoImage(self.img_cache)
		self.canvas.delete("all")
		self.canvas.create_image(0, 0, anchor="nw", image=self.pi)
		self.canvas.config(scrollregion=self.canvas.bbox("all"))

		if self.scale >= 1:
			self.canvas.config(width=max(self.old.winfo_screenwidth()/4,min(self.img_cache.width, self.old.winfo_screenwidth()/2**(1/2))), height=max(self.old.winfo_screenheight()/4, min(self.img_cache.height, self.old.winfo_screenheight()/2**(1/2))))

if __name__ == '__main__':

	Gui()