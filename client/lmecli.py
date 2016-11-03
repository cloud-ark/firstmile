import json 
import tarfile
import urllib2
import os
import codecs
import gzip
import sys

from Tkinter import *
import Tkinter as tk
from PIL import ImageTk, Image
import tkMessageBox, Tkconstants, tkFileDialog

DEVCENTRIC_IMAGE = "small-devcentric.png"

class LMEUI():
    
    def __init__1(self, root):
        #Frame.__init__(self, root)
        self.root = root


        self.root.mainloop()
        
    def set_welcome_screen(self):
        welcome_frame = Frame(self.root)
        welcome_frame.pack(side="bottom")
        
        self.root.title("Devcentric's LME")    
        #self.pack(fill=BOTH, expand=1)

        canvas = Canvas(welcome_frame)
        canvas.create_text(20, 30, anchor=W, font="Purisa",
            text="Most relationships seem so transitory")
        canvas.create_text(20, 60, anchor=W, font="Purisa",
            text="They're good but not the permanent one")
        canvas.create_text(20, 130, anchor=W, font="Purisa",
            text="Who doesn't long for someone to hold")
        canvas.create_text(20, 160, anchor=W, font="Purisa",
            text="Who knows how to love without being told")                   
        canvas.create_text(20, 190, anchor=W, font="Purisa",
            text="Somebody tell me why I'm on my own")            
        canvas.create_text(20, 220, anchor=W, font="Purisa",
            text="If there's a soulmate for everyone")               
        canvas.pack(fill=BOTH, expand=1)
        #self.root.mainloop()
        
    def deploy(self):
        print("Deploy called.")
    
    def track_deployment(self):
        print("Track deployment")
        
    def create_deployment(self):
        pass
    
    def askdirectory(self):
        dir_opt = options = {}
        options['initialdir'] = 'C:\\'
        options['mustexist'] = False
        options['parent'] = self.root
        options['title'] = 'This is a title'
        return tkFileDialog.askdirectory(dir_opt)

    #def create_deployment(self):
    def __init__(self, root):
        self.root = root
        print("Create a deployment")
        
        image_frame = Frame(self.root)
        image_frame.pack(fill=X)
        path = DEVCENTRIC_IMAGE
        img = ImageTk.PhotoImage(Image.open(path))
        img_label = tk.Label(image_frame, image = img)
        img_label.pack(side = "top", fill = "x", expand = "no")
        image_frame.pack(side="top")       
        
        frame0 = Frame(self.root)
        frame0.pack(fill=X)
        labelText_project=StringVar()
        labelText_project.set("Enter code path")
        labelDir=Label(frame0, textvariable=labelText_project, height=4)
        labelDir.pack(side="left")
        
        button_opt = {'fill': Tkconstants.BOTH, 'padx': 5, 'pady': 5}
        tk.Button(self, text='askdirectory', command=self.askdirectory).pack(**button_opt)        
        

        directory=StringVar(None, value="/home/devdatta/Code/packaging/samples/express-checkout")
        self.dirname=Entry(frame0,textvariable=directory,width=50)
        self.dirname.pack(side="left")
        
        frame1 = Frame(self.root)
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

        frame_r = Frame(self.root)
        frame_r.pack(fill=X)
        self.service_selection = IntVar()
        R1 = Radiobutton(frame_r, text="Use the existing service instance", variable=self.service_selection, value=0)
        R1.pack(side="left")

        R2 = Radiobutton(frame_r, text="Create a new service instance", variable=self.service_selection, value=1)
        R2.pack(side="left")

        framec = Frame(self.root)
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

        frame2 = Frame(self.root)
        frame2.pack()        
        
        b = Button(frame2, text="Deploy", command=self.deploy)
        b.pack(pady=50, side="left")
        
        track_button = Button(frame2, text="Track", command=self.track_deployment)
        track_button.pack(pady=50, side="left")


class Deployment(object):

    def __init__(self):
        pass

    def _make_tarfile(self, output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))

    def _read_tarfile(self, tarfile_name):
        with gzip.open(tarfile_name, "rb") as f:
            contents = f.read()
            return contents

    def post(self):
        source_dir = raw_input("Enter app directory:")
        k = source_dir.rfind("/")
        app_name = source_dir[k+1:]
        tarfile_name = app_name + ".tar"

        self._make_tarfile(tarfile_name, source_dir)
        tarfile_content = self._read_tarfile(tarfile_name)

        cloud = 'local'
        service_name = 'mysql-service'
        service_type = 'mysql'

        app_data = {'app_name':app_name, 'app_tar_name': tarfile_name, 
                    'app_content':tarfile_content, 'app_type': 'python',
                    'run_cmd': 'application.py'}
        cloud_data = {'cloud': cloud}

        service_details = {'db_var': 'DB', 'host_var': 'HOST', 
                           'user_var': 'USER', 'password_var': 'PASSWORD',
                           'db_name': 'checkout'}

        service_data = {'service_name':service_name, 'service_type': service_type, 
                        'service_details': service_details}

        data = {'app': app_data, 'service': [service_data], 'cloud': cloud_data}

        req = urllib2.Request("http://localhost:5000/deployments")
        req.add_header('Content-Type', 'application/octet-stream')

        response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=True, encoding='ISO-8859-1'))
        print("Deployment ID:%s" % response.headers.get('location'))

    def get(self, app_url):
        req = urllib2.Request(app_url)
        response = urllib2.urlopen(req)
        app_data = response.fp.read()
        print("Response:%s" % app_data)
        
def main():
    root = tk.Tk() # create a Tk root window

    w = 700 # width for the Tk root
    h = 700 # height for the Tk root

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
    
    lmeui_obj = LMEUI(root)
    #lmeui_obj.set_image()
    #lmeui_obj.set_welcome_screen()
    lmeui_obj.create_deployment()
    root.mainloop()
    
    dep = Deployment()

    if sys.argv[1].lower() == 'post':
        dep.post()
    if sys.argv[1].lower() == 'get':
        app_url = sys.argv[2]
        dep.get(app_url)

    print("Done.")    
    

if __name__ == '__main__':
    main()


