import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from labjack import ljm

handle = ljm.openS('Any', 'Any', 'ANY')
names = ['TDAC1', 'TDAC0']

# The parametrized function to be plotted
def f(t, amplitude, frequency):
    return amplitude * np.sin(2 * np.pi * frequency * t)

t = np.linspace(0, 1, 100)

# Define initial parameters
init_amplitude = 0
init_frequency = 0

init_x = 0.590
init_y = -0.289

ljm.eWriteNames(handle, len(names), names, [init_x, init_y])

# Create the figure and the line that we will manipulate
fig, ax = plt.subplots()
line, = ax.plot([init_x], [init_y], lw=2, marker = 'o')
ax.set_xlabel('X [v]')
ax.set_ylabel('Y [v]')

# adjust the main plot to make room for the sliders
fig.subplots_adjust(left=0.25, bottom=0.25)

# Make a horizontal slider to control the frequency.
axfreq = fig.add_axes([0.25, 0.1, 0.65, 0.03])
x_slider = Slider(
    ax=axfreq,
    label='x',
    valmin=-3,
    valmax=3,
    valinit=init_x,
)

# Make a vertically oriented slider to control the amplitude
axamp = fig.add_axes([0.1, 0.25, 0.0225, 0.63])
y_slider = Slider(
    ax=axamp,
    label="Y",
    valmin=-3,
    valmax=3,
    valinit=init_y,
    orientation="vertical"
)

ax.set_xlim(-3,3)
ax.set_ylim(-3,3)

# The function to be called anytime a slider's value changes
def update(val):
    #print(f"Frequency: {freq_slider.val}")
    #print(f"Amplitude: {amp_slider.val}")

    line.set_ydata(y_slider.val)
    line.set_xdata(x_slider.val)
    fig.canvas.draw_idle()

    ljm.eWriteNames(handle, len(names), names, [x_slider.val, y_slider.val])

# register the update function with each slider
x_slider.on_changed(update)
y_slider.on_changed(update)

# Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
resetax = fig.add_axes([0.8, 0.025, 0.1, 0.04])
button = Button(resetax, 'Reset', hovercolor='0.975')

def reset(event):
    x_slider.reset()
    y_slider.reset()
    ljm.eWriteNames(handle, len(names), names, [init_x, init_y])
    
button.on_clicked(reset)

plt.show()
ljm.eWriteNames(handle, len(names), names, [init_x, init_y])
ljm.close(handle)
