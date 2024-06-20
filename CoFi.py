import cv2 as cv
import numpy as np
import tkinter as tk
from tkinter import filedialog
from math import hypot as hp
from PIL import Image, ImageTk
from pywinauto import Application
from pywinauto.findwindows import find_windows
from os import remove
from yaml import dump as dump

class CoordinatesFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coordinates Finder")

        self.img = None
        self.cap = cv.VideoCapture()

        self.frame = tk.Frame(self.root)
        self.frame.pack()

        self.create_menu()

        self.canvas = tk.Canvas(self.root)
        self.canvas.pack()

        self.video_button_frame = tk.Frame(self.root)

        self.trackbars_frame = tk.Frame(self.root)
        self.create_sliders()
        self.create_save_push_buttons()

        self.calibrate_frame = tk.Frame(self.root)
        self.create_dim_calib_sliders()
        self.dim_calib_buttons()
        
        self.coordinate_option = tk.StringVar()
        self.coordinate_option.set("Center")

        self.dim_calib_option = tk.StringVar()
        self.dim_calib_option.set("Contour")  

        self.selected_dim_calib = tk.StringVar()
        self.create_dim_calib_radiobuttons()  
        self.selected_dim_calib_points = {"LT": None, "LD": None, "RD": None} 

        self.selected_coordinates = tk.StringVar()
        self.selected_coordinates.set("All")
        self.create_coordinate_radiobuttons()
        self.create_coordinate_entry()

        self.dim_coef = 1
        self.roi = []
        self.camera_matrix = []
        self.dist_coef = []
        self.origin = []

        self.newX = None
        self.newY = None

        self.update_closest_points = []

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.mainloop()

    def create_menu(self):
        menubar = tk.Menu(self.root)

        all_menu = tk.Menu(menubar, tearoff=0)
        all_menu.add_command(label="Open Local Video", command=self.open_local_video)
        all_menu.add_command(label="Open Online Video", command=self.open_online_video_window)
        all_menu.add_command(label="Open Image", command=self.open_image)
        all_menu.add_separator()
        all_menu.add_command(label="Save Settings", command=self.save_settings)
        all_menu.add_command(label="Load Settings", command=self.load_settings)
        all_menu.add_separator()
        all_menu.add_command(label="Calibrate Matrix", command=self.chess_board_calib)
        all_menu.add_command(label="Load Matrix Calibration", command=self.load_cb_calib)
        all_menu.add_command(label="Load Dimension Calibration", command=self.load_dim_calib)
        all_menu.add_separator()
        all_menu.add_command(label="Exit", command=self.on_close)

        open_menu = tk.Menu(menubar, tearoff=0)
        open_menu.add_command(label="Local Video", command=self.open_local_video)
        open_menu.add_command(label="Online Video", command=self.open_online_video_window)
        open_menu.add_command(label="Image", command=self.open_image)    

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Save", command=self.save_settings)
        settings_menu.add_command(label="Load", command=self.load_settings)

        calibration_menu = tk.Menu(menubar, tearoff=0)
        calibration_menu.add_command(label="Calibrate Matrix", command=self.chess_board_calib)
        calibration_menu.add_command(label="Load Matrix Calibration", command=self.load_cb_calib)
        calibration_menu.add_command(label="Load Dimension Calibration", command=self.load_dim_calib)

        menubar.add_cascade(label="All", menu=all_menu)
        menubar.add_cascade(label="Open", menu=open_menu)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        menubar.add_cascade(label="Calibrations", menu=calibration_menu)

        self.root.config(menu=menubar)

    def release_resources(self):
        if hasattr(self, 'img'):
            self.img = None
        if hasattr(self, 'img_tk'):
            self.img_tk = None
        if hasattr(self, 'video_button_frame'):
            self.video_button_frame.pack_forget()
        if hasattr(self, 'coordinate_option_menu'):
            self.coordinate_option_menu.pack_forget()
            del self.coordinate_option_menu
        if hasattr(self, 'dim_calib_option_menu'):
            self.dim_calib_option_menu.pack_forget()
            del self.dim_calib_option_menu
        if hasattr(self, 'x_entry'):
            self.x_entry.pack_forget()
            self.y_entry.pack_forget()            
        if hasattr(self, 'coordinate_radiobuttons'):
            for radiobutton in self.coordinate_radiobuttons.values():
                radiobutton.pack_forget() 
                del radiobutton
        if hasattr(self, 'dim_calib_radiobuttons'):
            for radiobutton in self.dim_calib_radiobuttons.values():
                radiobutton.pack_forget()  
                del radiobutton
        if hasattr(self, 'trackbars_frame'):
            self.trackbars_frame.pack_forget()
        if hasattr(self, 'calibrate_frame'):
            self.calibrate_frame.pack_forget()
        self.canvas.delete("all")

    def open_local_video(self):
        if self.cap.isOpened():
            self.cap.release()
        self.release_resources()
        self.cap = cv.VideoCapture(0)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
        self.open_video(self.cap)

    def open_online_video(self):
        if self.cap.isOpened():
            self.cap.release()
        self.release_resources()
        url = f'{self.url_entry.get()}/video'
        self.cap = cv.VideoCapture(url)
        self.open_video(self.cap)

    def open_online_video_window(self):
        online_video_window = tk.Toplevel(self.root)
        online_video_window.title("Online Video URL")

        url_label = tk.Label(online_video_window, text="Введите свой URL:")
        url_label.pack()

        self.url_entry = tk.Entry(online_video_window, width=50)
        self.url_entry.pack()
        self.url_entry.insert(tk.END, "https://10.54.70.200:8080")
        self.url_entry.bind("<Return>", lambda event: self.open_online_video())

    def open_video(self, cap):
        if cap:
            self.cap = cap
            self.video_button_frame.pack()
            self.create_video_buttons()
            self.update_video()

    def update_video(self, *args):
        ret, frame = self.cap.read()
        if ret:                                  
            self.canvas.unbind("<Button-1>")

            if len(self.dist_coef) != 0:
                h,  w = frame.shape[:2]
                new_camera_matrix, _ = cv.getOptimalNewCameraMatrix(self.camera_matrix, self.dist_coef, 
                                                                    (w,h), 1, (w,h))
                undistorted_frame = cv.undistort(frame, self.camera_matrix, 
                                                 self.dist_coef, None, new_camera_matrix)
                self.img = undistorted_frame
            else:
                self.img = frame

            if len(self.roi) != 0:
                self.img= self.img[self.roi[0][1]:self.roi[0][1]+self.roi[0][3], 
                                   self.roi[0][0]:self.roi[0][0]+self.roi[0][2]]
                cv.circle(self.img, (self.origin[0][0], self.origin[0][1]), 3, (0, 0, 255), -1)

            
                
            img_rgb = cv.cvtColor(self.img, cv.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            if img_pil.width > 1280 and img_pil.height > 720 and img_pil.width/img_pil.height == 16/9:
                img_pil_new = img_pil.resize((1280, 720))
                self.canvas.config(width=1280, height=720)
            elif img_pil.width > 960 and img_pil.height > 720 and img_pil.width/img_pil.height == 4/3:
                img_pil_new = img_pil.resize((960, 720))
                self.canvas.config(width=960, height=720)               
            else:
                img_pil_new = img_pil
                self.canvas.config(width=self.img.shape[1], height=self.img.shape[0])

            self.img_tk = ImageTk.PhotoImage(image=img_pil_new)

            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)

            self.root.after(50, self.update_video)
        else:
            print("Failed to read frame from camera.")

    def create_video_buttons(self):
        if not hasattr(self, 'save_image_button'):
            left_frame = tk.Frame(self.video_button_frame)
            right1_frame = tk.Frame(self.video_button_frame)
            right2_frame = tk.Frame(self.video_button_frame)
            right3_frame = tk.Frame(self.video_button_frame)
            
            left_frame.pack(side=tk.LEFT)
            right1_frame.pack(side=tk.RIGHT)
            right2_frame.pack(side=tk.RIGHT)
            right3_frame.pack(side=tk.RIGHT)
            

            self.show_button = tk.Button(left_frame, text="Find Coordinates", command=self.show_image)
            self.show_button.pack(side=tk.TOP, padx=5, pady=5)

            self.image_reset_button = tk.Button(left_frame, text="Image Reset", command=self.image_reset)
            self.image_reset_button.pack(side=tk.TOP, padx=5, pady=5)

            self.save_image_button = tk.Button(right1_frame, text="Save Image", command=self.save_image)
            self.save_image_button.pack(side=tk.TOP, padx=5, pady=5)

            self.save_and_show_button = tk.Button(right1_frame, text="Save and Show Image", command=self.save_and_show_image)
            self.save_and_show_button.pack(side=tk.TOP, padx=5, pady=5)

            self.calibrate_button = tk.Button(right2_frame, text="Calibrate Dimensity", command=self.dim_calibrate_open)
            self.calibrate_button.pack(side=tk.TOP, padx=5, pady=5)

            self.load_dim_calib_button = tk.Button(right2_frame, text="Load Dimension Calibration", command=self.load_dim_calib)
            self.load_dim_calib_button.pack(side=tk.TOP, padx=5, pady=5)

            self.save_cb_calib_button = tk.Button(right3_frame, text="Calibrate Matrix", command=self.chess_board_calib)
            self.save_cb_calib_button.pack(side=tk.TOP, padx=5, pady=5)

            self.load_cb_calib_button = tk.Button(right3_frame, text="Load Matrix Calibration", command=self.load_cb_calib)
            self.load_cb_calib_button.pack(side=tk.TOP, padx=5, pady=5)

    def show_image(self):
        filename = 'find_coord.jpg'
        cv.imwrite(filename, self.img)

        if self.cap.isOpened():
            self.cap.release()
        self.release_resources()        

        self.open_image_presets(filename)

        self.create_coordinate_option_menu()
        self.create_coordinate_entry()
        self.trackbars_frame.pack()
        self.update_image()

    def image_reset(self):
        self.camera_matrix = []
        self.dist_coef = []
        self.roi = []
        self.dim_coef = 1

    def save_image(self):
        filename = filedialog.asksaveasfilename(defaultextension=".", filetypes=(("PNG files", "*.png"), ("JPG files", "*.jpg"), ("All files", "*.*")))
        if filename:
            cv.imwrite(filename, self.img)
        
    def save_and_show_image(self):
        self.save_image()
        self.open_image()

    def load_dim_calib(self):
        filename = filedialog.askopenfilename(filetypes=(("Text files", "*.txt"), 
                                                         ("Yaml", "*.yaml"), ("All files", "*.*")))
        if filename:
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                
                self.origin = []
                self.roi = []

                for line in lines:
                    line = line.strip()
                    if line.startswith('- '):
                        if current_key == 'rect':
                            line = line.replace('- ', '')
                            self.roi[-1].append(int(line))
                        elif current_key == 'origin':
                            line = line.replace('- ', '')
                            self.origin[-1].append(int(line))                            
                    elif line.startswith('dim_coef'):
                        self.dim_coef = float(line.split(':')[-1].strip())
                    elif line.startswith('rect'):
                        current_key = 'rect'
                        self.roi.append([])
                    elif line.startswith('origin'):
                        current_key = 'origin'
                        self.origin.append([])

                self.roi = np.array(self.roi)
                self.origin = np.array(self.origin)

            except FileNotFoundError:
                print("Settings file not found.")

    def load_cb_calib(self):
        filename = filedialog.askopenfilename(filetypes=(("Text files", "*.txt"), 
                                                         ("Yaml", "*.yaml"), ("All files", "*.*")))
        if filename:
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                
                self.dist_coef = []
                self.camera_matrix = []
                current_key = None

                for line in lines:
                    line = line.strip()
                    if line.startswith('-'):
                        if current_key == 'camera_matrix':
                            line = line.replace('- ', '')
                            if len(self.camera_matrix[-1]) < 3:
                                self.camera_matrix[-1].append(float(line))
                            else:
                                self.camera_matrix.append([float(line)])
                        elif current_key == 'dist_coef':
                            line = line.replace('- ', '')
                            self.dist_coef[-1].append(float(line))
                    elif line.startswith('camera_matrix'):
                        current_key = 'camera_matrix'
                        self.camera_matrix.append([])
                    elif line.startswith('dist_coef'):
                        current_key = 'dist_coef'
                        self.dist_coef.append([])

                self.camera_matrix = np.array(self.camera_matrix)
                self.dist_coef = np.array(self.dist_coef)

            except FileNotFoundError:
                print("Settings file not found.")

    def chess_board_calib(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                filetypes=(("Text files", "*.txt"), 
                                                           ("Yaml", "*.yaml"), ("All files", "*.*")))
        if filename:

            criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            objp = np.zeros((9*6,3), np.float32)
            objp[:,:2] = np.mgrid[0:9,0:6].T.reshape(-1,2)

            objpoints = [] 
            imgpoints = [] 

            cap = cv.VideoCapture(0)
            cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
            while(True):
                ret, img = cap.read()
                gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

                ret, corners = cv.findChessboardCorners(gray, (9,6),None)

                if ret == True:
                    objpoints.append(objp)
                    corners2 = cv.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
                    imgpoints.append(corners2)
                    img = cv.drawChessboardCorners(img, (9,6), corners2, ret)

                if cv.waitKey(50) & 0xFF == ord('q'):
                    break

                cv.imshow('Chess board calibration', img)
                cv.waitKey(3000)

            cap.release()
            cv.destroyAllWindows()

            ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

            self.camera_matrix = mtx
            self.dist_coef = dist

            data = {'camera_matrix': np.asarray(mtx).tolist(), 'dist_coef': np.asarray(dist).tolist()}

            with open(f"{filename}", "w") as f:
                dump(data, f)

    def dim_calibrate_open(self):
        filename = f'calib.jpg'
        cv.imwrite(filename, self.img)

        if self.cap.isOpened():
            self.cap.release()
        self.release_resources()

        self.open_image_presets(filename)
        self.create_dim_calib_option_menu()
        self.create_dim_calib_radiobuttons()
        self.calibrate_frame.pack()        
        self.update_dim_calibrate()

    def update_dim_calibrate(self, *args):
        if self.img is not None:
            if self.dim_calib_option.get() == "Contour":
                self.canvas.unbind("<Button-1>")
                hsv_lower = np.array([
                    self.trackbars_calibrate["HMin"].get(),
                    self.trackbars_calibrate["SMin"].get(),
                    self.trackbars_calibrate["VMin"].get()
                ])
                hsv_upper = np.array([
                    self.trackbars_calibrate["HMax"].get(),
                    self.trackbars_calibrate["SMax"].get(),
                    self.trackbars_calibrate["Vmax"].get()
                ])

                hsv = cv.cvtColor(self.img, cv.COLOR_BGR2HSV)
                mask = cv.inRange(hsv, hsv_lower, hsv_upper)
                output = cv.bitwise_and(self.img, self.img, mask=mask)

                contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
                
                area_max = 0
                contour_max = None
                
                for contour in contours:
                    area = cv.contourArea(contour)
                    if area > area_max:
                        area_max = area
                        contour_max = contour
            
                if contour_max is not None:
                    approx = cv.approxPolyDP(contour_max, 0.001 * cv.arcLength(contour_max, True), True)
                    cv.drawContours(output, [approx], -1, (255, 0, 0), 2, cv.LINE_AA)

                self.x0_rect, self.y0_rect, self.rect_width, self.rect_height = cv.boundingRect(approx)
                cv.rectangle(output, (self.x0_rect, self.y0_rect), 
                             (self.x0_rect + self.rect_width, self.y0_rect + self.rect_height), (0, 255, 0), 1)
                rect_corners = np.array([[(self.x0_rect, self.y0_rect)], 
                                         [(self.x0_rect + self.rect_width, self.y0_rect)], 
                                         [(self.x0_rect, self.y0_rect + self.rect_height)], 
                                         [(self.x0_rect + self.rect_width, self.y0_rect + self.rect_height)]])

                closest_points = self.find_closest_points(rect_corners, approx)
                self.update_closest_points = closest_points

                for i, point in enumerate(closest_points):
                    x = point[0][0]
                    y = point[0][1]
                    string = f'x: {x}, y: {y}'

                    if i == 0:
                        cv.putText(output, string, (x - 50, y - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),
                                            lineType=cv.LINE_AA)
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                    elif i == 2:
                        cv.putText(output, string, (x - 50, y + 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                            lineType=cv.LINE_AA)
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                    elif i == 1:
                        cv.putText(output, string, (x, y - 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                            lineType=cv.LINE_AA)
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                    elif i == 3:
                        cv.putText(output, string, (x, y + 20), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                            lineType=cv.LINE_AA)
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)                        
            
            if self.dim_calib_option.get() == "Three points":
                output = self.img.copy()
                for key, value in self.selected_dim_calib_points.items():
                    if value is not None:
                        x, y = value
                        cv.circle(output, (x, y), 3, (0, 0, 255), -1)  
                        cv.putText(output, f'x{key}: {x}, y{key}: {y}', (x, y - 20), cv.FONT_HERSHEY_SIMPLEX, 
                                   0.5, (255, 0, 0), lineType=cv.LINE_AA)  
                        
                if self.selected_dim_calib_points['LD'] is not None:        
                    cv.line(output, self.selected_dim_calib_points['LT'], self.selected_dim_calib_points['LD'], 
                            (255, 0, 0), 2, lineType=cv.LINE_AA)
                if (self.selected_dim_calib_points['LD'] and self.selected_dim_calib_points['RD']) is not None:
                    cv.line(output, self.selected_dim_calib_points['LD'], self.selected_dim_calib_points['RD'], 
                            (255, 0, 0), 2, lineType=cv.LINE_AA)
                    
                if (self.selected_dim_calib_points['LT'] and self.selected_dim_calib_points['RD']) is not None:
                    self.x0_rect = self.selected_dim_calib_points['LT'][0] - 15
                    self.y0_rect = self.selected_dim_calib_points['LT'][1] - 15
                    self.rect_width = self.selected_dim_calib_points['RD'][0] - self.x0_rect + 15 
                    self.rect_height = self.selected_dim_calib_points['RD'][1] - self.y0_rect + 15 
                    cv.rectangle(output, (self.x0_rect, self.y0_rect), 
                             (self.x0_rect + self.rect_width, self.y0_rect + self.rect_height), (0, 255, 0), 1)
                                    
            img_pil = Image.fromarray(cv.cvtColor(output, cv.COLOR_BGR2RGB))
            if img_pil.width > 1280 and img_pil.height > 720 and img_pil.width/img_pil.height == 16/9:
                img_pil_new = img_pil.resize((1280, 720), Image.LANCZOS)
            elif img_pil.width > 960 and img_pil.height > 720 and img_pil.width/img_pil.height == 4/3:
                img_pil_new = img_pil.resize((960, 720), Image.LANCZOS)
                self.canvas.config(width=960, height=720)
            else: 
                img_pil_new = img_pil
            self.img_tk = ImageTk.PhotoImage(image=img_pil_new)

            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
            self.toggle_dim_calib_radiobutton_visibility()

    def create_dim_calib_option_menu(self):
        if not hasattr(self, 'dim_calib_option'):
            return

        self.dim_calib_option_menu = tk.OptionMenu(self.frame, self.dim_calib_option, "Contour", "Three points",command=self.update_dim_calibrate)
        self.dim_calib_option_menu.pack(side=tk.LEFT, padx=5, pady=5)    

    def create_dim_calib_radiobuttons(self):
        self.dim_calib_radiobuttons = {}
        coordinate_options = [("LT", "Left Top"), ("LD", "Left Down"), ("RD", "Right Down")]

        for key, text in coordinate_options:
            radiobutton = tk.Radiobutton(self.frame, text=text, variable=self.selected_dim_calib, value=key,
                                            command=lambda key=key: self.canvas.bind("<Button-1>", self.canvas_click_handler(key)))
            self.dim_calib_radiobuttons[key] = radiobutton

    def canvas_click_handler(self, key):
        def handler(event):
            x = event.x
            y = event.y
            self.selected_dim_calib_points[key] = (x, y)
            self.update_dim_calibrate()
        return handler
        
    def toggle_dim_calib_radiobutton_visibility(self):
        if self.dim_calib_option.get() == "Three points":
            for slider in self.trackbars_calibrate.values():
                slider.pack_forget()            
            for radiobutton in self.dim_calib_radiobuttons.values():
                radiobutton.pack(side=tk.LEFT, padx=5, pady=5)
        else:          
            for radiobutton in self.dim_calib_radiobuttons.values():
                radiobutton.pack_forget()
            for slider in self.trackbars_calibrate.values():
                slider.pack(side=tk.LEFT, padx=5, pady=5)  

    def create_dim_calib_sliders(self):
        self.trackbars_calibrate = {}
        sliders_info = [
            ("HMin", 0, 179),
            ("SMin", 0, 255),
            ("VMin", 0, 255),
            ("HMax", 0, 179),
            ("SMax", 0, 255),
            ("Vmax", 0, 255)
        ]

        for name, min_val, max_val in sliders_info:
            slider_frame = tk.Frame(self.calibrate_frame)
            slider_frame.pack(side=tk.LEFT, fill=tk.X)

            label = tk.Label(slider_frame, text=name)
            label.pack(side=tk.BOTTOM)
            
            slider = tk.Scale(slider_frame, from_=min_val, to=max_val, 
                              orient=tk.HORIZONTAL, command=self.update_dim_calibrate)
            
            if name == "HMin" or name == "SMin" or name == "VMin":
                slider.set(min_val)
            else:
                slider.set(max_val)

            self.trackbars_calibrate[name] = slider
        
    def dim_calib_buttons(self):
        save_dim_calib_button = tk.Button(self.calibrate_frame, text="Save and Calibrate", command=self.save_dim_calib)
        save_dim_calib_button.pack(side=tk.TOP, padx=5, pady=5)

        load_dim_calib_button = tk.Button(self.calibrate_frame, text="Load Dimension Calibration", command=self.load_dim_calib)
        load_dim_calib_button.pack(side=tk.TOP, padx=5, pady=5)  

    def save_dim_calib(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                filetypes=(("Text files", "*.txt"), 
                                                           ("Yaml", "*.yaml"), ("All files", "*.*")))
        if filename:
            if self.dim_calib_option.get() == "Contour":
                closest_points = self.update_closest_points
                px_line = hp(closest_points[0][0][0] - closest_points[2][0][0], 
                             closest_points[0][0][1] - closest_points[2][0][1])
                dim_coef = float(400)/px_line
                self.dim_coef = dim_coef

                roi = [[self.x0_rect, self.y0_rect, self.rect_width, self.rect_height]]
                self.roi = roi

                x0 = closest_points[2][0][0]
                y0 = closest_points[2][0][1]

                origin = [[x0-roi[0][0], y0-roi[0][1]]]
                self.origin = origin

            elif self.dim_calib_option.get() == "Three points":
                
                px_line = hp(self.selected_dim_calib_points['LT'][0] - self.selected_dim_calib_points['LD'][0], 
                             self.selected_dim_calib_points['LT'][1] - self.selected_dim_calib_points['LD'][1])
                dim_coef = float(400)/px_line
                self.dim_coef = dim_coef

                roi = [[self.x0_rect, self.y0_rect, self.rect_width, self.rect_height]]
                self.roi = roi

                x0 = self.selected_dim_calib_points['LD'][0]
                y0 = self.selected_dim_calib_points['LD'][1]

                origin = [[x0-roi[0][0], y0-roi[0][1]]]
                self.origin = origin 

            data = {'dim_coef': dim_coef, 'rect': roi, 'origin': np.asarray(origin).tolist()}

            with open(filename, "w") as f:
                dump(data, f)

    def open_image_presets(self, filename):
        self.img = cv.imread(filename)

        img_pil = Image.fromarray(cv.cvtColor(self.img, cv.COLOR_BGR2RGB))
        if img_pil.width > 1280 and img_pil.height > 720 and img_pil.width/img_pil.height == 16/9:
            img_pil_new = img_pil.resize((1280, 720), Image.LANCZOS)
            self.canvas.config(width=1280, height=720)
        elif img_pil.width > 960 and img_pil.height > 720 and img_pil.width/img_pil.height == 4/3:
            img_pil_new = img_pil.resize((960, 720), Image.LANCZOS)
            self.canvas.config(width=690, height=720)
        else:
            img_pil_new = img_pil
            self.canvas.config(width=self.img.shape[1], height=self.img.shape[0])

        self.img_tk = ImageTk.PhotoImage(image=img_pil_new)
        self.original_img = np.copy(self.img)

    def open_image(self):
        if self.cap.isOpened():
            self.cap.release()
        self.release_resources()

        filename = filedialog.askopenfilename() 
        self.open_image_presets(filename)

        self.create_coordinate_option_menu()
        self.create_coordinate_entry()
        self.trackbars_frame.pack()
        self.update_image()

    def update_image(self, *args):
        if self.img is not None:
            if len(self.origin) != 0:
                cv.circle(self.img, (self.origin[0][0], self.origin[0][1]), 3, (0, 0, 255), -1)

            hsv_lower = np.array([
                self.trackbars["HMin"].get(),
                self.trackbars["SMin"].get(),
                self.trackbars["VMin"].get()
            ])
            hsv_upper = np.array([
                self.trackbars["HMax"].get(),
                self.trackbars["SMax"].get(),
                self.trackbars["Vmax"].get()
            ])

            hsv = cv.cvtColor(self.img, cv.COLOR_BGR2HSV)
            mask = cv.inRange(hsv, hsv_lower, hsv_upper)
            output = cv.bitwise_and(self.img, self.img, mask=mask)

            contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
            
            area_max = 0
            contour_max = None
            
            for contour in contours:
                area = cv.contourArea(contour)
                if area > area_max:
                    area_max = area
                    contour_max = contour

            if contour_max is not None:
                approx = cv.approxPolyDP(contour_max, 0.001 * cv.arcLength(contour_max, True), True)
                cv.drawContours(output, [approx], -1, (255, 0, 0), 2, cv.LINE_AA)

            if hasattr(self, 'coordinate_option'):
                if self.coordinate_option.get() == "Center":
                    self.canvas.unbind("<Button-1>")
                    M = cv.moments(contour_max)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                    cv.circle(output, (cx, cy), 5, (0, 0, 255), -1)
                    cv.putText(output, f'px - x: {cx}, y: {cy}', (cx - 40, cy - 20), cv.FONT_HERSHEY_SIMPLEX, 
                               0.5, (255, 0, 0), lineType=cv.LINE_AA)

                    if len(self.roi) != 0:
                        self.newX = format((int(cx) - int(self.origin[0][0])) * self.dim_coef, '.3f')
                        self.newY = format((int(self.origin[0][1]) - int(cy)) * self.dim_coef, '.3f')
                        cv.putText(output, f'mm - x: {self.newX}, y: {self.newY}', (cx - 40, cy - 40), 
                                   cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), lineType=cv.LINE_AA)
                    
                elif self.coordinate_option.get() == "Your point":
                    self.canvas.bind("<Button-1>", self.create_your_point)

                elif self.coordinate_option.get() == "Offset point":
                    self.canvas.unbind("<Button-1>")
                    if hasattr(self, 'x_entry'):
                        self.x_entry.pack_forget()
                        self.y_entry.pack_forget()
                    self.create_coordinate_entry()

                    x0, y0, rect_width, rect_height = cv.boundingRect(approx)
                    cv.rectangle(output, (x0, y0), (x0 + rect_width, y0 + rect_height), (0, 255, 0), 1)
                    rect_corners = np.array([[(x0, y0)], 
                                             [(x0 + rect_width, y0)], 
                                             [(x0, y0 + rect_height)], 
                                             [(x0 + rect_width, y0 + rect_height)]])

                    closest_points = self.find_closest_points(rect_corners, approx)

                    self.update_closest_points = closest_points
                    self.update_offset_point()

                    for i, point in enumerate(closest_points):
                        x = point[0][0]
                        y = point[0][1]
                        if len(self.roi) != 0:
                            newX = format((int(x) - int(self.origin[0][0])) * self.dim_coef, '.3f')
                            newY = format((int(self.origin[0][1]) - int(y)) * self.dim_coef, '.3f')

                        string = f'px - x: {x}, y: {y}'

                        if (self.selected_coordinates.get() == "LT" or self.selected_coordinates.get() == "All") and i == 0:
                            if len(self.roi) != 0:
                                cv.putText(output, f'mm - x: {newX}, y: {newY}', (x - 50, y - 50), 
                                                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0),
                                                    lineType=cv.LINE_AA) 
                            cv.putText(output, string, (x - 50, y - 20), cv.FONT_HERSHEY_SIMPLEX, 
                                       0.5, (0, 255, 0), lineType=cv.LINE_AA)
                            cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                        elif (self.selected_coordinates.get() == "LD" or self.selected_coordinates.get() == "All") and i == 2:
                            if len(self.roi) != 0:
                                cv.putText(output, f'mm - x: {newX}, y: {newY}', (x - 50, y + 50), 
                                                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                                    lineType=cv.LINE_AA) 
                            cv.putText(output, string, (x - 50, y + 20), cv.FONT_HERSHEY_SIMPLEX, 
                                       0.5, (255, 0, 0), lineType=cv.LINE_AA)
                            cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                        elif (self.selected_coordinates.get() == "RT" or self.selected_coordinates.get() == "All") and i == 1:
                            if len(self.roi) != 0:
                                cv.putText(output, f'mm - x: {newX}, y: {newY}', (x, y - 50), 
                                                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                                    lineType=cv.LINE_AA) 
                            cv.putText(output, string, (x, y - 20), cv.FONT_HERSHEY_SIMPLEX, 
                                       0.5, (255, 0, 0), lineType=cv.LINE_AA)
                            cv.circle(output, (x, y), 3, (0, 0, 255), -1)
                        elif (self.selected_coordinates.get() == "RD" or self.selected_coordinates.get() == "All") and i == 3:
                            if len(self.roi) != 0:
                                cv.putText(output, f'mm - x: {newX}, y: {newY}', (x, y + 50), 
                                                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0),
                                                    lineType=cv.LINE_AA) 
                            cv.putText(output, string, (x, y + 20), cv.FONT_HERSHEY_SIMPLEX, 
                                       0.5, (255, 0, 0), lineType=cv.LINE_AA)
                            cv.circle(output, (x, y), 3, (0, 0, 255), -1)                        

            img_pil = Image.fromarray(cv.cvtColor(output, cv.COLOR_BGR2RGB))
            if img_pil.width > 1280 and img_pil.height > 720 and img_pil.width/img_pil.height == 16/9:
                img_pil_new = img_pil.resize((1280, 720),Image.LANCZOS)
            elif img_pil.width > 960 and img_pil.height > 720 and img_pil.width/img_pil.height == 4/3:
                img_pil_new = img_pil.resize((960, 720),Image.LANCZOS)
                self.canvas.config(width=960, height=720)
            else: 
                img_pil_new = img_pil
            self.img_tk = ImageTk.PhotoImage(image=img_pil_new)

            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
            self.toggle_coordinate_entry_visibility()
            self.toggle_coordinate_radiobutton_visibility()
            
        else:
            print("No image to update.")

    def create_coordinate_option_menu(self):
        if not hasattr(self, 'coordinate_option'):
            return

        self.coordinate_option_menu = tk.OptionMenu(self.frame, self.coordinate_option, "Center", "Offset point", "Your point",command=self.update_image)
        self.coordinate_option_menu.pack(side=tk.LEFT, padx=5, pady=5)

    def create_sliders(self):
        self.trackbars = {}
        sliders_info = [
            ("HMin", 0, 179),
            ("SMin", 0, 255),
            ("VMin", 0, 255),
            ("HMax", 0, 179),
            ("SMax", 0, 255),
            ("Vmax", 0, 255)
        ]

        for name, min_val, max_val in sliders_info:
            slider_frame = tk.Frame(self.trackbars_frame)
            slider_frame.pack(side=tk.LEFT, fill=tk.X)

            label = tk.Label(slider_frame, text=name)
            label.pack(side=tk.BOTTOM)
            
            slider = tk.Scale(slider_frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, command=self.update_image)
            
            if name == "HMin" or name == "SMin" or name == "VMin":
                slider.set(min_val)
            else:
                slider.set(max_val)

            slider.pack(side=tk.LEFT, padx=5, pady=5)
            self.trackbars[name] = slider

    def create_save_push_buttons(self):
        left_frame = tk.Frame(self.trackbars_frame)
        right_frame = tk.Frame(self.trackbars_frame)

        left_frame.pack(side=tk.LEFT)
        right_frame.pack(side=tk.RIGHT)

        push_button = tk.Button(left_frame, text="Push Origin", command=self.push_origin_button)
        push_set_button = tk.Button(left_frame, text="Push And Set Origin", command=self.push_set_origin_button)
        save_button = tk.Button(right_frame, text="Save Settings", command=self.save_settings)
        load_button = tk.Button(right_frame, text="Load Settings", command=self.load_settings)

        save_button.pack(side=tk.TOP, padx=5, pady=5)
        load_button.pack(side=tk.TOP, padx=5, pady=5)
        push_button.pack(side=tk.TOP, padx=5, pady=5)
        push_set_button.pack(side=tk.TOP, padx=5, pady=5)

    def save_settings(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if filename:
            settings = {}
            for name, slider in self.trackbars.items():
                settings[name] = slider.get()
            with open(filename, "w") as f:
                for name, value in settings.items():
                    f.write(f"{name}: {value}\n")

    def load_settings(self):
        filename = filedialog.askopenfilename(filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if filename:
            try:
                with open(filename, "r") as f:
                    for line in f:
                        name, value = line.strip().split(": ")
                        self.trackbars[name.strip()].set(int(value.strip()))
            except FileNotFoundError:
                print("Settings file not found.")

    def open_app_window(self):
        windows = find_windows(title='MDX-540[RML-1] - VPanel', top_level_only=True)
        app = Application(backend="uia").connect(handle=windows[0])
        self.main_window = app.window(title='MDX-540[RML-1] - VPanel') 

    def push_origin_button(self):
        self.open_app_window()

        if self.main_window.exists():
            if self.main_window.is_minimized():
                self.main_window.restore()
            if not self.main_window.is_active():
                self.main_window.set_focus()    

        self.main_window.child_window(title="Move Tool", control_type="Button").click()
        tool_move_window = self.main_window.child_window(title="Tool Movement", control_type="Window")
        tool_move_window.child_window(auto_id='1035').set_text(f'{self.newX}')
        tool_move_window.child_window(auto_id='1041').set_text(f'{self.newY}')
        tool_move_window.child_window(auto_id='1029').click()
        tool_move_window.close()

    def push_set_origin_button(self):
        self.push_origin_button()

        self.main_window.child_window(title="Base Point", control_type="Button").click()
        base_point_window = self.main_window.child_window(title="Set Base Point", control_type="Window")
        base_point_window.child_window(auto_id='1348').click()

    def create_coordinate_radiobuttons(self):
        self.coordinate_radiobuttons = {}
        coordinate_options = [("All", "All Corners"),
                              ("LT", "Left Top"), 
                              ("LD", "Left Down"), 
                              ("RT", "Right Top"), 
                              ("RD", "Right Down")]

        for key, text in coordinate_options:
            radiobutton = tk.Radiobutton(self.frame, text=text, variable=self.selected_coordinates, 
                                         value=key, command=self.update_image)
            self.coordinate_radiobuttons[key] = radiobutton

    def toggle_coordinate_radiobutton_visibility(self):
        if self.coordinate_option.get() == "Offset point":
            for radiobutton in self.coordinate_radiobuttons.values():
                radiobutton.pack(side=tk.LEFT, padx=5, pady=5)
        else:
            for radiobutton in self.coordinate_radiobuttons.values():
                radiobutton.pack_forget()

    def create_coordinate_entry(self):
        self.x_entry = tk.Entry(self.frame, width=10)
        self.x_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.y_entry = tk.Entry(self.frame, width=10)
        self.y_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.x_entry.pack()
        self.y_entry.pack()

        self.x_entry.bind("<Return>", self.update_offset_point)
        self.y_entry.bind("<Return>", self.update_offset_point)

        self.toggle_coordinate_entry_visibility()

    def update_offset_point(self, event=None):
        newX = self.x_entry.get()
        newY = self.y_entry.get()

        if newX and newY:
            x = int((float(newX)/self.dim_coef))
            y = int((float(newY)/self.dim_coef))
            try:
                if self.img is not None:
                    self.img = np.copy(self.original_img)

                    closest_points = self.update_closest_points

                    selected_point = None
                    if self.selected_coordinates.get() == "LT":
                        selected_point = closest_points[0]
                        x_ref = selected_point[0][0] + x
                        y_ref = selected_point[0][1] + y
                        self.offset_point(x_ref, y_ref)
                    elif self.selected_coordinates.get() == "LD":
                        selected_point = closest_points[2]
                        x_ref = selected_point[0][0] + x
                        y_ref = selected_point[0][1] - y
                        self.offset_point(x_ref, y_ref)
                    elif self.selected_coordinates.get() == "RT":
                        selected_point = closest_points[1]
                        x_ref = selected_point[0][0] - x
                        y_ref = selected_point[0][1] + y
                        self.offset_point(x_ref, y_ref)                           
                    elif self.selected_coordinates.get() == "RD":
                        selected_point = closest_points[3]
                        x_ref = selected_point[0][0] - x
                        y_ref = selected_point[0][1] - y
                        self.offset_point(x_ref, y_ref)

            except ValueError:
                print("Please enter valid integers for x and y coordinates.")
        else:
            pass

    def offset_point(self, x_ref, y_ref):
        if len(self.roi) != 0:
            self.newX = format((int(x_ref) - int(self.origin[0][0])) * self.dim_coef, '.3f')
            self.newY = format((int(self.origin[0][1]) - int(y_ref)) * self.dim_coef, '.3f')
            cv.putText(self.img, f'mm - x: {self.newX}, y: {self.newY}', (x_ref - 40, y_ref - 30), cv.FONT_HERSHEY_SIMPLEX, 
                       0.4, (255, 0, 0), lineType=cv.LINE_AA) 
        cv.putText(self.img, f'px - x: {x_ref}, y: {y_ref}', (x_ref - 40, y_ref - 10), cv.FONT_HERSHEY_SIMPLEX, 
                   0.4, (0, 255, 0), lineType=cv.LINE_AA)
        cv.circle(self.img, (x_ref, y_ref), 3, (0, 0, 255), -1)
        self.update_image()

    def find_closest_points(self, rect_corners, approx):
        closest_points = []

        for corner in rect_corners:
            min_dist = float('inf')
            closest_point = None
            for point in approx:
                dist = hp(point[0][0] - corner[0][0], point[0][1] - corner[0][1])
                if dist < min_dist:
                    min_dist = dist
                    closest_point = point
            closest_points.append(closest_point)

        return closest_points
    
    def toggle_coordinate_entry_visibility(self, *args):
        if self.coordinate_option.get() == "Offset point":  
            if (not hasattr(self, 'x_entry')):
                self.create_coordinate_entry()
        else:
            self.x_entry.pack_forget()
            self.y_entry.pack_forget()

    def create_your_point(self, event):
        self.img = np.copy(self.original_img)
        x = event.x
        y = event.y

        if len(self.roi) != 0:
            self.newX = format((int(x) - int(self.origin[0][0])) * self.dim_coef, '.3f')
            self.newY = format((int(self.origin[0][1]) - int(y)) * self.dim_coef, '.3f')
            cv.putText(self.img, f'mm - x: {self.newX}, y: {self.newY}', (x - 40, y - 30), 
                                   cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), lineType=cv.LINE_AA) 
        cv.putText(self.img, f'px - x: {x}, y: {y}', (x - 40, y - 10), cv.FONT_HERSHEY_SIMPLEX, 
                   0.4, (0, 255, 0), lineType=cv.LINE_AA)     
        cv.circle(self.img, (x, y), 3, (0, 0, 255), -1)
        self.update_image()

    def on_close(self):
        files_to_delete = ["find_coord.jpg", "calib.jpg"]
        for file in files_to_delete:
            try:
                remove(file)
                print(f"{file} удален.")
            except FileNotFoundError:
                print(f"{file} не найден.")
        self.root.quit()

root = tk.Tk()
app = CoordinatesFinderApp(root)
