import tkinter as tk

# Assume these are set elsewhere in your code
window_start = 0
window_end = 20
LastByteAcked = 5
LastByteSent = 10
LastByteWritten = 15

# Create the main Tkinter window
root = tk.Tk()

# Create a canvas to draw the rectangles
canvas = tk.Canvas(root, width=500, height=200)
canvas.pack()

# Calculate the width of each rectangle based on the canvas width
rect_width = canvas['width']
rect_width = int(rect_width) / (window_end - window_start + 1)

# Draw the rectangles
for i in range(window_start, window_end + 1):
    color = "white"
    if i <= LastByteAcked:
        color = "blue"
    elif i <= LastByteSent:
        color = "green"
    elif i <= LastByteWritten:
        color = "red"
    canvas.create_rectangle(i * rect_width, 0, (i + 1) * rect_width, 200, fill=color)

root.mainloop()