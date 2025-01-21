import plotly.graph_objects as go
import numpy as np
import ipywidgets as widgets
from IPython.display import display

class PIDController:
    def __init__(self, W):
        self.kp = 50
        self.ti = 1
        self.td = 0.01
        self.integral = 0.0
        self.prev_error = 0.0
        self.clamp_min, self.clamp_max = -W, W

    def symulacja_PID(self, setpoint, measured_value, tp):
        error = setpoint - measured_value
        self.integral += error * tp
        self.integral = np.clip(self.integral, -self.clamp_max / self.kp, self.clamp_max / self.kp)
        derivative = (error - self.prev_error) / tp
        output = self.kp * (error + (tp / self.ti) * self.integral + (self.td / tp) * derivative)
        output = np.clip(output, self.clamp_min, self.clamp_max)
        self.prev_error = error
        return output

def symulacja(setpoint):
    st, total_time = 0.1, 3600
    ambient_temp, num_people = 15.0, 0
    heat_per_person, k_loss, V, g, c, W = 0.0428, 5.0, 30.0, 1.225, 1005.0, 1500
    heat_capacity = V * g * c

    pid = PIDController(W=W)
    current_temp = ambient_temp

    time_points, temperature_points = [], []

    for t in range(int(total_time / st)):
        raw_output = pid.symulacja_PID(setpoint, current_temp, st)

        thermostat = np.clip(raw_output, -W, W)

        heat_loss = k_loss * (current_temp - ambient_temp)
        people_heat = num_people * heat_per_person
        dT = (thermostat - heat_loss + people_heat) / heat_capacity * st
        current_temp += dT

        time_points.append(t * st)
        temperature_points.append(current_temp)

    plot_results(time_points, temperature_points, setpoint, ambient_temp)

def plot_results(time_points, temperature_points, setpoint, ambient):
    # Create temperature plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=time_points, y=temperature_points, mode='lines', name=f'Temperatura zadana: {setpoint}°C'))

    fig.add_trace(go.Scatter(x=[0, time_points[-1]], y=[ambient, ambient],
                             mode='lines', name='Temperatura otoczenia', line=dict(dash='dash')))

    fig.update_layout(
        title='Symulacja temperatury',
        xaxis_title='Czas [s]',
        yaxis_title='Temperatura [°C]',
        legend_title='Legenda',
        template='plotly_white'
    )

    fig.show()

def create_input_widget():
    setpoint_input = widgets.FloatText(
        value=22.0,
        description='Setpoint (°C):',
        step=0.1
    )

    simulate_button = widgets.Button(
        description='Run Simulation',
        button_style='success'
    )

    output = widgets.Output()

    def on_button_click(b):
        with output:
            output.clear_output()
            symulacja(setpoint_input.value)

    simulate_button.on_click(on_button_click)

    display(widgets.VBox([setpoint_input, simulate_button, output]))

if __name__ == "__main__":
    create_input_widget()
