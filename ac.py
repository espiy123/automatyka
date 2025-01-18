import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import numpy as np
import random

class PIDController:
    def __init__(self, kp, tp, ti, td):
        self.kp = kp
        self.ti = ti
        self.td = td
        self.tp = tp
        self.integral = 0.0
        self.prev_error = 0.0

    def symulacja_PID(self, setpoint, measured_value):
        error = setpoint - measured_value
        self.integral += self.prev_error

        derivative = (error - self.prev_error)/self.tp

        output = self.kp * (
            error
            + (self.tp/ self.ti) * self.integral
            + self.td * derivative
        )
        self.prev_error = error
        return output

def heat_loss_model(current_temp, external_temp, window_open, wall_thickness):
    block_ratio = 0.8
    insulation_ratio = 0.2
    k_block = 1.2
    k_insulation = 0.04

    k_wall = (block_ratio / k_block + insulation_ratio / k_insulation) ** -1
    wall_area = 10.0
    heat_loss = (k_wall * wall_area * (current_temp - external_temp)) / (wall_thickness / 100)

    if window_open:
        air_density = 1.225
        specific_heat_air = 1005
        g = 9.81
        h = 0.1
        delta_temp = abs(current_temp - external_temp)
        external_temp_k = external_temp + 273.15

        airflow_velocity = 0.5 * np.sqrt(g * h * delta_temp / external_temp_k)
        airflow_rate = airflow_velocity

        heat_loss += airflow_rate * air_density * specific_heat_air * (current_temp - external_temp)

    return heat_loss

def generate_random_openings(total_time, num_events=5):
    events = []
    for _ in range(num_events):
        start_time = random.uniform(0, total_time - 60)
        duration = random.uniform(5, 60)
        events.append((start_time, start_time + duration))
    return events

def calculate_overshoot(temperature_points, setpoint):
    h_max = max(temperature_points)
    h_ust = setpoint
    overshoot = (h_max - h_ust) / h_ust * 100
    return overshoot

def symulacja(
    setpoint,
    initial_temp,
    total_time,
    ac_power,
    external_temp,
    manual_window_open,
    random_openings,
    wall_thickness,
    kp, ti, td, tp
):

    room_volume = 40.0

    air_density = 1.225
    specific_heat_air = 1005
    heat_capacity = room_volume * air_density * specific_heat_air

    pid = PIDController(kp=kp, tp=tp, ti=ti, td=td)
    current_temp = initial_temp

    time_points = []
    temperature_points = []

    steps = int(total_time / tp)

    for i in range(steps):
        current_time = i * tp

        window_open = manual_window_open
        for start, end in random_openings:
            if start <= current_time <= end:
                window_open = True
                break

        raw_output = pid.symulacja_PID(setpoint, current_temp)
        thermostat = np.clip(raw_output,0,ac_power)
        loss = heat_loss_model(current_temp, external_temp, window_open, wall_thickness)
        dT = (thermostat - loss) / heat_capacity * tp
        current_temp += dT

        time_points.append(current_time/60)
        temperature_points.append(current_temp)

    overshoot = calculate_overshoot(temperature_points, setpoint)
    print(f"Przeregulowanie: {overshoot:.2f}%")
    print(f"P = {kp}, I = {ti}, D = {td}")

    return time_points, temperature_points

def plot_results(time_points, temperature_points, setpoint):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[round(t, 1) for t in time_points],
        y=[round(temp, 1) for temp in temperature_points],
        mode='lines',
        name='Temperatura [°C]'
    ))
    fig.add_hline(y=setpoint, line_color="red", annotation_text=f"Setpoint = {setpoint}°C")

    fig.update_layout(
        title="Symulacja temperatury (tylko grzejnik, brak przycinania PID)",
        xaxis_title='Czas [minuty]',
        yaxis_title='Temperatura [°C]',
        legend_title='Legenda',
        template='plotly_white'
    )
    return fig

app = dash.Dash(__name__)
app.title = "Symulacja grzejnika"

app.layout = html.Div([
    html.H1("Symulacja temperatury (tylko grzejnik, bez ograniczenia PID)",
            style={"textAlign": "center", "color": "#6666FF"}),

    html.Div([
        # --- KOLUMNA 1 ---
        html.Div([
            html.Label("Wartość zadana (°C)", style={"fontWeight": "bold"}),
            dcc.Input(
                id="setpoint-input", type="number", value=22.0, step=0.1,
                debounce=True, style={"width": "100%", "marginBottom": "10px"}
            ),

            html.Label("Temperatura zewnętrzna (°C)", style={"fontWeight": "bold"}),
            dcc.Input(
                id="external-temp-input", type="number", value=5.0, step=0.1,
                debounce=True, style={"width": "100%", "marginBottom": "10px"}
            ),
        ], style={"width": "30%", "display": "inline-block",
                  "verticalAlign": "top", "padding": "10px"}),

        # --- KOLUMNA 2 ---
        html.Div([
            html.Label("Grubość ściany [cm]", style={"fontWeight": "bold"}),
            dcc.Slider(
                id="wall-thickness-slider", min=20, max=100, step=1, value=40,
                marks={20: "20", 60: "60", 100: "100"}
            ),

            html.Label("Maksymalna moc grzejnika [W]",
                       style={"fontWeight": "bold", "marginTop": "15px"}),
            dcc.Input(
                id="ac-power-input", type="number", value=1500, step=100,
                debounce=True, style={"width": "100%", "marginBottom": "10px"}
            ),

            html.Button(
                id="window-button", children="Otwórz okno", n_clicks=0,
                style={"marginTop": "15px", "width": "100%"}
            ),
            html.Button(
                id="random-events-button", children="Losuj otwarcia okna", n_clicks=0,
                style={"marginTop": "15px", "width": "100%"}
            ),
        ], style={"width": "30%", "display": "inline-block",
                  "verticalAlign": "top", "padding": "10px"}),

        # --- KOLUMNA 3 ---
        html.Div([
            html.Label("Parametr kp", style={"fontWeight": "bold"}),
            dcc.Slider(
                id="kp-slider", min=0, max=10, step=0.1, value=2,
                marks={0: "0", 5: "5", 10: "10"}, tooltip={"placement": "bottom"}
            ),

            html.Label("Parametr ti", style={"fontWeight": "bold", "marginTop": "15px"}),
            dcc.Slider(
                id="ti-slider", min=0, max=100, step=0.1, value=12,
                marks={0: "0", 50: "50", 100: "100"}, tooltip={"placement": "bottom"}
            ),

            html.Label("Parametr td", style={"fontWeight": "bold", "marginTop": "15px"}),
            dcc.Slider(
                id="td-slider", min=0, max=100, step=0.1, value=2,
                marks={0: "0", 50: "50", 100: "100"}, tooltip={"placement": "bottom"}
            ),

            html.Label("Czas próbkowania (tp) [s]", style={"fontWeight": "bold", "marginTop": "15px"}),
            dcc.Slider(
                id="tp-slider", min=0.1, max=100, step=0.1, value=1,
                marks={0.1: "0.1", 5: "5", 10: "10"}, tooltip={"placement": "bottom"}
            ),
        ], style={"width": "30%", "display": "inline-block",
                  "verticalAlign": "top", "padding": "10px"}),

    ], style={
        "padding": "20px",
        "border": "1px solid #ccc",
        "borderRadius": "10px",
        "backgroundColor": "#f9f9f9",
        "margin": "0 auto",
        "maxWidth": "1200px"
    }),

    html.Div([
        dcc.Graph(id="temperature-graph")
    ], style={"padding": "20px", "marginTop": "30px",
              "width": "100%", "maxWidth": "100%"})
], style={"margin": "auto"})

@app.callback(
    [
        Output("temperature-graph", "figure"),
        Output("window-button", "children"),
        Output("random-events-button", "n_clicks")
    ],
    [
        Input("setpoint-input", "value"),
        Input("ac-power-input", "value"),
        Input("external-temp-input", "value"),
        Input("wall-thickness-slider", "value"),
        Input("kp-slider", "value"),
        Input("ti-slider", "value"),
        Input("td-slider", "value"),
        Input("tp-slider", "value"),
        Input("window-button", "n_clicks"),
        Input("random-events-button", "n_clicks")
    ]
)
def update_graph(
    setpoint, ac_power, external_temp,
    wall_thickness, kp, ti, td, tp,
    n_clicks, random_n_clicks
):
    total_time = 7200  # 2h symulacji
    initial_temp = 15.0

    # Okno otwarte, jeśli liczba kliknięć jest nieparzysta
    manual_window_open = (n_clicks % 2 == 1)
    button_label = "Zamknij okno" if manual_window_open else "Otwórz okno"

    # Losowe otwarcia okna
    if random_n_clicks > 0:
        random_openings = generate_random_openings(total_time)
    else:
        random_openings = []

    # Symulacja (bez przycinania wyjścia PID)
    time_points, temperature_points = symulacja(
        setpoint=setpoint,
        initial_temp=initial_temp,
        total_time=total_time,
        ac_power=ac_power,
        external_temp=external_temp,
        manual_window_open=manual_window_open,
        random_openings=random_openings,
        wall_thickness=wall_thickness,
        kp=kp, ti=ti, td=td, tp=tp
    )

    fig = plot_results(time_points, temperature_points, setpoint)

    # Po wywołaniu wykresu zerujemy n_clicks od random-events-button
    return fig, button_label, 0

if __name__ == "__main__":
    app.run_server(debug=True)
