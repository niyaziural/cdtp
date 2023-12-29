import multiprocessing
import os
import tkinter
import time
import turtle

from heuristic import Rectangle
from idbs import IDBS
from tkinter import filedialog

DEF_SERVO_UP = "M03"
DEF_SERVO_DOWN = "M05"
DEF_TRAVEL_SPEED = "2000"
DEF_DRAWING_SPEED = "1000"
DEF_UP_ANGLE = "30"
DEF_DOWN_ANGLE = "60"
DEF_DELAY = "0.2"

DEF_TABU_SEQ_LENGTH = 10
DEF_TABU_TENURE = 3

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")

A4_WIDTH = 21.0
A4_HEIGHT = 29.7

class UI:
    def __init__(self) -> None:
        # Main window
        self.window = tkinter.Tk()
        self.window.title("Two Dimensional Strip Packer")
        self.window.config(padx=50, pady=50)
        # Solution draw area
        self.canvas = tkinter.Canvas()
        self.canvas.config(width=500, height=500, borderwidth=10, relief="raised")
        self.canvas.grid(row=0, column=2, rowspan=50)
        # How many new sequences to be generated in tabu search
        self.tabu_seq_length_slider = tkinter.Scale(label="Tabu search new sequence count", length=250, from_=5, to=15, orient="horizontal")
        self.tabu_seq_length_slider.set(DEF_TABU_SEQ_LENGTH)
        self.tabu_seq_length_slider.grid(row=0, column=0, padx=(0, 50), sticky="S")
        # Tenure multiplier for how long an item stays in the tabu list
        self.tabu_tenure_slider = tkinter.Scale(label="Tabu tenure", length=250, from_=2, to=4, orient="horizontal")
        self.tabu_tenure_slider.set(DEF_TABU_TENURE)
        self.tabu_tenure_slider.grid(row=1, column=0, padx=(0, 50), sticky="N")
        # Open test file button
        self.open_file_button = tkinter.Button(text="Open test file", command=self.open_test_file)
        self.open_file_button.grid(row=2, column=0, padx=(0, 50))
        # Run button
        self.run_button = tkinter.Button(text="Run", state="disabled", command=self.run)
        self.run_button.grid(row=50, column=0, padx=(0, 50))
        # Save gcode for the solution button
        self.gcode_button = tkinter.Button(text="Save G-code", state="disabled", command=self.save_gcode)
        self.gcode_button.grid(row=50, column=2)
        # Console area to write logs
        self.text_widget = tkinter.Text(wrap="word", height=20, width=50)
        self.text_widget.grid(row=3, column=0, rowspan=47, padx=(0, 50))
        # Turtle for drawing
        self.t = turtle.RawTurtle(canvas=self.canvas, visible=False)
        # Events to inform other deamons to terminate if one of them finds a solution
        self.quit = multiprocessing.Event()
        self.found = multiprocessing.Event()

    def start(self):
        """Starts the UI"""
        self.window.mainloop()

    def draw_rectangle(self, bottom_left_pos, width, height, scale=1, start_x=0, start_y=0):
        """Draws a rectangle on UI object's canvas"""
        self.t.speed(0)
        self.t.hideturtle()
        self.t.penup()
        self.t.goto((bottom_left_pos[0] * scale + start_x, bottom_left_pos[1] * scale + start_y))
        self.t.pendown()
        self.t.forward(width * scale)
        self.t.left(90)
        self.t.forward(height * scale)
        self.t.left(90)
        self.t.forward(width * scale)
        self.t.left(90)
        self.t.forward(height * scale)
        self.t.left(90)


    def draw_sequence(self, sequence: list[Rectangle], scale=1, start_x=0, start_y=0):
        """Draws a list of rectangles on UI object's canvas."""
        # Disable all the buttons while drawing
        self.open_file_button.config(state="disabled")
        self.run_button.config(state="disabled")
        self.gcode_button.config(state="disabled")
        # Clear the previous drawing
        self.t.reset()

        for rectangle in sequence:
            if rectangle.bottom_left_pos:
                width = rectangle.height if rectangle.rotate else rectangle.width
                height = rectangle.width if rectangle.rotate else rectangle.height
                self.draw_rectangle(rectangle.bottom_left_pos, width, height, scale, start_x, start_y)
        # Activate the buttons back
        self.open_file_button.config(state="active")
        self.run_button.config(state="active")
    
    def open_test_file(self):
        """Opens a dialog box for user to pick a Hopper-Turton's C test file to load."""
        file_path = filedialog.askopenfilename(initialdir=DATA_DIR, title="Select a file", filetypes=[("All files", "C*_*")])
        if file_path:
            self.rectangles = []
            # Read bin width, bin height and rectangles from the test file
            with open(file_path, "r") as dataset:
                self.text_widget.config(state="normal")
                self.text_widget.delete(1.0, tkinter.END)  # Clear previous content
                rectangle_count = int(dataset.readline())
                self.bin_width, self.bin_height = map(int, dataset.readline().split(" "))

                for i in range(rectangle_count):
                    rec_width, rec_height = map(int, dataset.readline().split(" ")[:2])
                    # Log each rectangle to the console
                    self.text_widget.insert(
                        tkinter.END, f"{i + 1:<4}- width: {rec_width:<3} | height: {rec_height}\n"
                    )
                    rectangle = Rectangle(rec_width, rec_height)
                    self.rectangles.append(rectangle)
            # Log the test file informations to the consoe   
            self.text_widget.insert(tkinter.END, f"--------\nFile: {os.path.basename(file_path)}\n")
            self.text_widget.insert(tkinter.END, f"Rectangle count: {rectangle_count}\n")
            self.text_widget.insert(tkinter.END, f"Bin width: {self.bin_width}\n")
            self.text_widget.insert(tkinter.END, f"Optimum height: {self.bin_height}\n--------\n")
            self.text_widget.see(tkinter.END)
            self.text_widget.config(state="disabled")

            self.run_button.config(state="active")


    def run(self):
        """Run's the IDBS(Iterative Doubling Binary Search) for the loaded Hopper-Turton C test file."""
        # Clear the events for multiprocessing
        self.quit.clear()
        self.found.clear()
        # Make the console area editable
        self.text_widget.config(state="normal")
        self.text_widget.insert(tkinter.END, "Running...\n")
        # Move the cursor to the end of the console
        self.text_widget.see(tkinter.END)
        # Queue for daemons to put their solution into
        return_queue = multiprocessing.Queue()
        # Get the configuration values from the sliders on the UI
        tabu_seq_length = self.tabu_seq_length_slider.get()
        tabu_tenure = self.tabu_tenure_slider.get()
        # Set the timer
        t0 = time.time()
        # Create an iterative doubling binary search object
        idbs = IDBS(100, self.bin_width, self.bin_height, tabu_seq_length, tabu_tenure)
        # Create half of the core count new processes and run
        for _ in range(multiprocessing.cpu_count() // 2):
            p = multiprocessing.Process(
                target=idbs.run, args=(self.rectangles, self.quit, self.found, return_queue)
            )
            p.start()
        # Wait for the found event from one of the processes
        self.found.wait()
        # Set the quit event for other events to terminate themselves
        self.quit.set()
        # Get the solution from the queue
        best_seq = return_queue.get()
        # Check if the solution is an optimal solution and log it
        if best_seq[1] == self.bin_height:
            self.text_widget.insert(tkinter.END, f"An optimal solution found in: {time.time() - t0:.2f}s\n")
        else:
            self.text_widget.insert(tkinter.END, f"A near optimal solution found with height of {best_seq[1]} in: {time.time() - t0:.2f}s\n")
        self.text_widget.see(tkinter.END)
        # Disable the console area
        self.text_widget.config(state="disabled")
        self.canvas.update()
        # Adjust the starting point of the drawing to fit the solution on the canvas
        scale = self.canvas.winfo_height() / (max(self.bin_width, self.bin_height) * 1.1)
        start_x = -(self.bin_width * scale) // 2
        start_y = -(self.bin_height * scale) // 2
        # Sort the solution by x and y values to draw rectangles from bottom to top
        best_seq[0].sort(key=lambda x: x.bottom_left_pos[0])
        best_seq[0].sort(key=lambda x: x.bottom_left_pos[1])
        self.best_seq = best_seq[0]
        self.draw_sequence(best_seq[0], scale, start_x, start_y)
        self.gcode_button.config(state="active")

    def save_gcode(self):
        """Opens a new window to adjust gcode generation settings."""
        self.new_window = tkinter.Toplevel(self.window, padx=20, pady=20)
        self.new_window.title("G-Code Generator")
    
        # Settings' labels
        tkinter.Label(self.new_window, text ="Servo up command:").grid(row=0, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Servo down command:").grid(row=1, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Travel speed:").grid(row=2, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Drawing speed:").grid(row=3, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Servo up angle:").grid(row=4, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Servo down angle:").grid(row=5, column=0, sticky="w")
        tkinter.Label(self.new_window, text ="Delay:").grid(row=6, column=0, sticky="w")

        # Setting entries
        self.up_command = tkinter.Entry(self.new_window, width=8)
        self.down_command = tkinter.Entry(self.new_window, width=8)
        self.travel_speed = tkinter.Entry(self.new_window, width=8)
        self.draw_speed = tkinter.Entry(self.new_window, width=8)
        self.up_angle = tkinter.Entry(self.new_window, width=8)
        self.down_angle = tkinter.Entry(self.new_window, width=8)
        self.delay = tkinter.Entry(self.new_window, width=8)
        
        try:
            # Load the settings if there is a save file
            with open(os.path.join(DATA_DIR, "g_code_settings.txt"), "r") as f:
                self.up_command.insert(0, f.readline().rstrip("\n"))
                self.down_command.insert(0, f.readline().rstrip("\n"))
                self.travel_speed.insert(0, f.readline().rstrip("\n"))
                self.draw_speed.insert(0, f.readline().rstrip("\n"))
                self.up_angle.insert(0, f.readline().rstrip("\n"))
                self.down_angle.insert(0, f.readline().rstrip("\n"))
                self.delay.insert(0, f.readline().rstrip("\n"))
        except FileNotFoundError:
            # Populate with the default values if there is no save file
            self.up_command.insert(0, DEF_SERVO_UP)
            self.down_command.insert(0, DEF_SERVO_DOWN)
            self.travel_speed.insert(0, DEF_TRAVEL_SPEED)
            self.draw_speed.insert(0, DEF_DRAWING_SPEED)
            self.up_angle.insert(0, DEF_UP_ANGLE)
            self.down_angle.insert(0, DEF_DOWN_ANGLE)
            self.delay.insert(0, DEF_DELAY)

        # Place elements on the window
        self.up_command.grid(row=0, column= 1, sticky="e")
        self.down_command.grid(row=1, column= 1, sticky="e")
        self.travel_speed.grid(row=2, column= 1, sticky="e")
        self.draw_speed.grid(row=3, column= 1, sticky="e")
        self.up_angle.grid(row=4, column= 1, sticky="e")
        self.down_angle.grid(row=5, column= 1, sticky="e")
        self.delay.grid(row=6, column=1, sticky="e")
        
        # Cancel and generate buttons
        generate_button = tkinter.Button(self.new_window, text="Generate", command=self.generate_gcode)
        cancel_button = tkinter.Button(self.new_window, text="Cancel", command=self.new_window.destroy)
        # Place the buttons
        generate_button.grid(row=7, column=1)
        cancel_button.grid(row=7, column=0)
    
    def generate_gcode(self):
        """Generates G-Code for the solution and saves it to the file chosen by the user."""
        # Save the settings to a save file
        with open(os.path.join(DATA_DIR,"g_code_settings.txt"), "w") as f:
            f.write(f"{self.up_command.get()}\n")
            f.write(f"{self.down_command.get()}\n")
            f.write(f"{self.travel_speed.get()}\n")
            f.write(f"{self.draw_speed.get()}\n")
            f.write(f"{self.up_angle.get()}\n")
            f.write(f"{self.down_angle.get()}\n")
            f.write(f"{self.delay.get()}\n")
        # Ask for the save location
        file_path = filedialog.asksaveasfilename(title="Select a destination", initialfile="servo.gcode", defaultextension=".gcode", filetypes=[("G-Code Files", "*.gcode")])
        if file_path:
            # Common G-Code commands generated from the settings
            up_command = f"{self.up_command.get()} S{self.up_angle.get()}\n"
            down_command = f"{self.down_command.get()} S{self.down_angle.get()}\n"
            travel_speed = f"G1 F{self.travel_speed.get()}\n"
            draw_speed = f"G1 F{self.draw_speed.get()}\n"
            delay = f"G4 P{self.delay.get()}\n"
            # Check if the solution will fit on an A4 paper
            scale = 1
            if self.bin_width > A4_WIDTH:
                # Scale down factor
                scale = (A4_WIDTH - 1) / self.bin_width
            elif self.bin_height > A4_HEIGHT:
                # Scale down factor
                scale = (A4_HEIGHT - 1) / self.bin_height
            
            with open(file_path, "w") as f:
                # First raise the pen and give the settings
                f.write(f"{up_command}\nG90\nG21\n")
                # For each rectangle in the solution
                for rec in self.best_seq:
                    # Bottom left position of the rectangle
                    x, y = rec.bottom_left_pos
                    x, y = (x * scale, y * scale)
                    # Check if the rectangle is rotated in the solution
                    width, height = (rec.width, rec.height) if not rec.rotate else (rec.height, rec.width)
                    width, height = (width * scale, height * scale)
                    # Set move speed to travel speed since the pen is up
                    f.write(travel_speed)
                    # Go to bottom left position of the rectangle
                    f.write(f"G1 X{x} Y{y}\n")
                    f.write(delay)
                    # Lower the pen
                    f.write(down_command)
                    f.write(delay)
                    # Set move speed to drawing speed
                    f.write(draw_speed)
                    # Draw each side of the rectangle
                    f.write(f"G1 X{x + width} Y{y}\n")
                    f.write(f"G1 X{x + width} Y{y + height}\n")
                    f.write(f"G1 X{x} Y{y + height}\n")
                    f.write(f"G1 X{x} Y{y}\n")
                    f.write(delay)
                    # Raise the pen
                    f.write(up_command)
                    f.write(delay)
                f.write(travel_speed)
                # Go to origin at the end
                f.write(f"G1 X0 Y0")
                # Close the previously opened new window
                self.new_window.destroy()
