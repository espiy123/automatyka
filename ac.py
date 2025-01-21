import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go


class PID:
    def __init__(self, Kp, Ti, Td, dt, u_min, u_max):
        self.Kp = Kp
        self.Ti = Ti
        self.Td = Td
        self.dt = dt
        self.u_min = u_min
        self.u_max = u_max
        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, setpoint, measurement):
        error = setpoint - measurement
        if self.Ti != 0:
            self.integral += (self.dt / self.Ti) * error
        else:
            self.integral = 0.0
        derivative = 0.0
        if self.Td != 0:
            derivative = (self.Td / self.dt) * (error - self.prev_error)
        u = self.Kp * (error + self.integral + derivative)
        if u > self.u_max:
            u = self.u_max
        elif u < self.u_min:
            u = self.u_min
        self.prev_error = error
        return u


def simulate_2h(Kp, Ti, Td, T_sp, T_init=20.0, dt=1.0, T_outside=15.0, max_power=2000.0, window_open=False):
    VOLUME = 4.0 * 4.0 * 2.5
    AIR_DENSITY = 1.2
    AIR_CAPACITY = 1005.0
    MASS = VOLUME * AIR_DENSITY
    C = MASS * AIR_CAPACITY

    U_DOOR = 1.3
    DOOR_AREA = 1.8

    U_WINDOW = 0.9
    WINDOW_AREA = 1.35

    U_ROOF = 0.15
    ROOF_AREA = 16

    U_GROUND = 0.3
    GROUND_AREA = 16

    U_WALL = 0.2
    WALL_AREA = 40.0 - DOOR_AREA - WINDOW_AREA

    SIM_TIME = int(7200 / dt)
    pid = PID(Kp=Kp, Ti=Ti, Td=Td, dt=dt, u_min=0, u_max=max_power)
    pid.reset()
    time_array = []
    temp_array = []
    T_room = T_init
    VENT_FLOW = 0.03

    for t in range(SIM_TIME):
        time_array.append(t * dt / 60)
        temp_array.append(T_room)

        heat_loss_walls = U_WALL * WALL_AREA * (T_room - T_outside)
        heat_loss_vent = VENT_FLOW * AIR_DENSITY * AIR_CAPACITY * (T_room - T_outside)
        heat_loss_door = U_DOOR * DOOR_AREA * (T_room - T_outside)
        heat_loss_window = U_WINDOW * WINDOW_AREA * (T_room - T_outside)

        if window_open:
            heat_loss_window *= 5  # Zwiększenie strat ciepła, gdy okno jest otwarte

        heat_loss_roof = U_ROOF * ROOF_AREA * (T_room - T_outside)
        heat_loss_ground = U_GROUND * GROUND_AREA * (T_room - T_outside)

        total_heat_loss = (heat_loss_walls + heat_loss_vent + heat_loss_door +
                           heat_loss_window + heat_loss_roof + heat_loss_ground)

        power_grzejnik = pid.update(T_sp, T_room) * 0.9

        dT = (power_grzejnik - total_heat_loss) / C * dt
        T_room += dT

    return time_array, temp_array


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
app.title = "Symulacja ogrzewania (PID) – 2h"

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Symulacja ogrzewania pokoju", className="text-center text-primary mb-4"),
                width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("Parametry symulacji", className="text-primary"),
                dbc.Label("Kp:"),
                dcc.Slider(
                    id='input-kp',
                    min=1,
                    max=20,
                    step=0.1,
                    value=5,
                    marks={i: str(i) for i in range(1, 21, 2)}
                ),
                dbc.Label("Ti [s]:"),
                dcc.Slider(
                    id='input-ti',
                    min=0,
                    max=100,
                    step=1,
                    value=70,
                    marks={i: str(i) for i in range(0, 101, 10)}
                ),
                dbc.Label("Td [s]:"),
                dcc.Slider(
                    id='input-td',
                    min=0,
                    max=100,
                    step=1,
                    value=10,
                    marks={i: str(i) for i in range(0, 101, 10)}
                ),
                dbc.Label("Czas próbkowania [s]:"),
                dcc.Slider(
                    id='input-dt',
                    min=0.1,
                    max=20,
                    step=0.1,
                    value=1.0,
                    marks={i: str(i) for i in range(1, 21, 2)}
                ),
                dbc.Label("Temperatura zadana (°C):"),
                dbc.Input(
                    id='input-setpoint',
                    type='number',
                    value=25.0,
                    step=0.5
                ),
                dbc.Label("Temperatura na zewnątrz (°C):"),
                dbc.Input(
                    id='input-outside-temp',
                    type='number',
                    value=15.0,
                    step=0.5
                ),
                dbc.Label("Moc grzejnika (W):"),
                dcc.Slider(
                    id='input-max-power',
                    min=0,
                    max=2000,
                    step=500,
                    value=2000,
                    marks={i: f'{i} W' for i in range(0, 2001, 500)}
                ),
                html.Div([
                    dbc.Button(
                        "Otwórz okno", id='open-window', color='danger', className="mt-3 me-2", n_clicks=0
                    ),
                    dbc.Button(
                        "Zamknij okno", id='close-window', color='success', className="mt-3", n_clicks=0
                    ),
                ], className="d-flex justify-content-between")
            ], className="border p-3 shadow-sm")
        ], width=3),
        dbc.Col([
            dcc.Graph(id='graph-temperature')
        ], width=9)
    ])
], fluid=True)



@app.callback(
    Output('graph-temperature', 'figure'),
    [
        Input('input-kp', 'value'),
        Input('input-ti', 'value'),
        Input('input-td', 'value'),
        Input('input-dt', 'value'),
        Input('input-setpoint', 'value'),
        Input('input-outside-temp', 'value'),
        Input('input-max-power', 'value'),
        Input('open-window', 'n_clicks'),
        Input('close-window', 'n_clicks')
    ],
    State('graph-temperature', 'figure')
)
def update_figure(kp, ti, td, dt, setpoint, outside_temp, max_power, open_clicks, close_clicks, current_figure):
    Kp = kp if kp is not None else 100.0
    Ti = ti if ti is not None else 75.0
    Td = td if td is not None else 10.0
    dt = dt if dt is not None else 1.0
    T_sp = setpoint if setpoint is not None else 25.0
    T_outside = outside_temp if outside_temp is not None else 15.0
    max_power = max_power if max_power is not None else 2000.0

    # Okno otwarte, jeśli liczba kliknięć „Otwórz” > liczba kliknięć „Zamknij”
    window_open = open_clicks > close_clicks

    time_array, temp_array = simulate_2h(
        Kp, Ti, Td, T_sp, dt=dt, T_outside=T_outside, max_power=max_power, window_open=window_open)

    trace_temp = go.Scatter(
        x=time_array,
        y=temp_array,
        mode='lines',
        name='Temperatura (°C)',
        line=dict(color='red')
    )

    fig_temp = go.Figure(data=[trace_temp], layout=go.Layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Temperatura (°C)')
    ))
    return fig_temp


if __name__ == '__main__':
    app.run_server(debug=True)
