#!/usr/bin/python

# Taken from: http://stackoverflow.com/questions/14910858/how-to-specify-where-a-tkinter-window-opens

from Tkinter import *
import Tkinter as tk
from PIL import ImageTk, Image
import tkMessageBox, tkFont, Tkconstants, tkFileDialog
import deployment as dp

frame4 = NONE

class LME(Frame):
        
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.app_directory = ''
        self.dep_track_url = ''
         
        self.parent = parent
        self.dirname = ''
        self.cloud_option = ''
        self.service1 = ''
        self.service2 = ''
        self.portValue = ''
        self.service_selection = 0
        self.track_frame = Frame(self.parent)
        
        menu = Menu(self)
        self.parent.config(menu=menu)
        filemenu = Menu(menu)
        menu.add_cascade(label="Deployment", menu=filemenu)
        filemenu.add_command(label="Create", command=self.create_deployment)
        filemenu.add_command(label="Track", command=self.track_deployment)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.parent.quit)

        helpmenu = Menu(menu)
        menu.add_cascade(label="Help", menu=helpmenu)
        helpmenu.add_command(label="Best practices", command=self.best_practices)
        helpmenu.add_command(label="Glossary", command=self.glossary)        
        helpmenu.add_command(label="About", command=self.about)

        frame3 = Frame(self.parent)
        frame3.pack(side="top")

        path = "small-devcentric.png"
        img = ImageTk.PhotoImage(Image.open(path))
        panel = tk.Label(frame3, image = img)
        panel.pack(side = "top", fill = "x", expand = "no")
        
        # defining options for opening a directory
        self.dir_opt = options = {}
        options['initialdir'] = 'C:\\'
        options['mustexist'] = False
        options['parent'] = parent
        options['title'] = 'This is a title'
        self.parent.mainloop()

    def deploy(self):
        print("Deploy the app")
        project_location = self.dirname.get()
        #project_location = self.app_directory
        print("Dir name:%s" % project_location)
        
        
        cloud_picked = self.cloud_option.get()
        print("Cloud picked:%s" % cloud_picked)
        if cloud_picked == 'Local':
            service1 = self.service1.get()
            #app_port = self.portValue.get()
            app_port = '5000'
            service_selection= self.service_selection.get()
            print("Local cloud dep.")
            
            app_info = {}
            app_info['app_type'] = 'python'
            app_info['entrypoint'] = 'application.py'
            
            service_info = {}
            service_info['service_name'] = 'mysql-service'
            service_info['service_type'] = 'mysql'
            
            dep = dp.Deployment()
            self.dep_track_url = dep.post(project_location, app_info, service_info, cloud='local')
            print("App tracking url:%s" % self.dep_track_url)
        else:
            print("Option not supported.")
            
        if self.track_frame:
            self.track_frame.pack_forget()
        self.track_frame = Frame(self.parent)
        self.track_frame.pack()

        status_text = Text(self.track_frame)
        status_text.insert(INSERT, "Deployment url:" + self.dep_track_url)
        status_text.pack(side="bottom")
            
    def askdirectory(self):
        self.directory = tkFileDialog.askdirectory(**self.dir_opt)
        print("Selected directory:%s" % self.directory)

    def create_deployment(self):
        print("Create a deployment")
        
        space_frame = Frame(self.parent)
        space_frame.pack(fill=Y)

        frame0 = Frame(self.parent)
        frame0.pack(fill=X)
        labelText_project=StringVar()
        labelText_project.set("Specify application folder")
        labelDir=Label(frame0, textvariable=labelText_project, height=4)
        labelDir.pack(side="left")
        
        # options for buttons
        #button_opt = {'padx': 5, 'pady': 5}
        #tk.Button(frame0, text='Browse', 
        #          command=self.askdirectory).pack(**button_opt)
        #app_selector.pack(side="left")

        directory=StringVar(None, value="")
        self.dirname=Entry(frame0,textvariable=directory,width=50)
        self.dirname.pack(side="left")

        frame1 = Frame(self.parent)
        frame1.pack(fill=X)
        
        serviceText = StringVar()
        serviceText.set("Select service dependency")
        serviceLabel = Label(frame1, textvariable=serviceText, height=4)
        serviceLabel.pack(side="left")
        
        service_opts = ["MySQL", "MongoDB"]
        self.service1 = StringVar(frame1)
        self.service1.set(service_opts[0])
        w = apply(OptionMenu, (frame1, self.service1) + tuple(service_opts))
        w.pack(side="left")        

        frame_r = Frame(self.parent)
        frame_r.pack(fill=X)
        self.service_selection = IntVar()
        R1 = Radiobutton(frame_r, text="Use the existing service instance", variable=self.service_selection, value=0)
        R1.pack(side="left")

        R2 = Radiobutton(frame_r, text="Create a new service instance", variable=self.service_selection, value=1)
        R2.pack(side="left")

        framec = Frame(self.parent)
        framec.pack(fill=X)
        
        labelText_cloud=StringVar()
        labelText_cloud.set("Choose cloud")
        labelDir=Label(framec, textvariable=labelText_cloud, height=4)
        labelDir.pack(side="left")      
        
        OPTIONS = [
            "Local",
            "Amazon",
            "Google"
        ]
        self.cloud_option = StringVar(framec)
        self.cloud_option.set(OPTIONS[0]) # default value
        w = apply(OptionMenu, (framec, self.cloud_option) + tuple(OPTIONS))
        w.pack(side="left")

        frame2 = Frame(self.parent)
        frame2.pack()        
        
        b = Button(frame2, text="Deploy", command=self.deploy)
        b.pack(pady=50, side="left")
        
        #track_button = Button(frame2, text="Track", command=self.track_deployment)
        #track_button.pack(pady=50, side="left")

    def track_deployment(self):
        print("Track a deployment")
        project_location = self.dirname.get()
        print("Dir name:%s" % project_location)
        
        cloud_picked = self.cloud_option.get()
        print("Cloud picked:%s" % cloud_picked)
        
        if self.track_frame:
            self.track_frame.pack_forget()
        self.track_frame = Frame(self.parent)
        self.track_frame.pack()

        if cloud_picked == 'Local':
            dep = dp.Deployment()
            status = dep.get(self.dep_track_url)
        elif cloud_picked == 'Google':
            status = "Tracking for Google not implemented yet."
            print(status)
        elif cloud_picked == 'Amazon':
            status = "Tracking for Amazon not implemented yet."
            print(status)

        status_text = Text(self.track_frame)
        status_text.insert(INSERT, status)
        status_text.pack(side="bottom")

    def best_practices(self):
        print("Best practices")    
    
    def glossary(self):
        print("Glossary")
        
    def about(self):
        print("About")

def main():
    root = tk.Tk() # create a Tk root window
    
    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=11)
    root.option_add("*Font", default_font)

    w = 900 # width for the Tk root
    h = 800 # height for the Tk root

    # get screen width and height
    ws = root.winfo_screenwidth() # width of the screen
    hs = root.winfo_screenheight() # height of the screen

    # calculate x and y coordinates for the Tk root window
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)

    # set the dimensions of the screen 
    # and where it is placed
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    root.wm_title("Local Multi-cloud Engine")
    app = LME(root)

if __name__ == '__main__':
    main()