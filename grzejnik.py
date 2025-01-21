import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

class PI:
    def __init__(self, kp, Ti, Tp, u_min, u_max):
        self.kp = kp  # Wzmocnienie proporcjonalne
        self.Ti = Ti  # Czas zdwojenia
        self.Tp = Tp  # Okres próbkowania
        self.u_min = u_min  # Minimalna wartość sygnału sterującego
        self.u_max = u_max  # Maksymalna wartość sygnału sterującego
        self.u_prev = 0.0  # Poprzednia wartość sygnału sterującego
        self.e_prev = 0.0  # Poprzedni błąd regulacji

    def reset(self):
        self.u_prev = 0.0
        self.e_prev = 0.0

    def update(self, setpoint, measurement):
        e = setpoint - measurement  # Błąd regulacji
        delta_e = e - self.e_prev  # Przyrost błędu

        # Obliczanie przyrostu sygnału sterującego
        delta_u = self.kp * (delta_e + (self.Tp / self.Ti) * e)

        # Nowa wartość sygnału sterującego
        u = self.u_prev + delta_u

        # Ograniczenia sygnału sterującego (nasycenie)
        u = max(min(u, self.u_max), self.u_min)

        # Aktualizacja stanu
        self.e_prev = e
        self.u_prev = u

        return u

def simulate_2h(kp, Ti, T_sp, T_init=20.0, Tp=1.0, T_outside=15.0, max_power=15000.0):
    VOLUME = 4.0 * 4.0 * 2.5
    AIR_DENSITY = 1.2
    AIR_CAPACITY = 1005.0
    MASS = VOLUME * AIR_DENSITY
    C = MASS * AIR_CAPACITY

    BUFFER_MASS = 50.0 * AIR_CAPACITY  # Bufor cieplny
    TOTAL_C = C + BUFFER_MASS  # Całkowita pojemność cieplna

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

    SIM_TIME = int(14400 / Tp)
    pi = PI(kp=kp, Ti=Ti, Tp=Tp, u_min=0, u_max=max_power)
    pi.reset()
    time_array = []
    temp_array = []
    T_room = T_init

    for t in range(SIM_TIME):
        time_array.append(t * Tp / 60)
        temp_array.append(T_room)

        heat_loss_walls = U_WALL * WALL_AREA * (T_room - T_outside)
        heat_loss_door = U_DOOR * DOOR_AREA * (T_room - T_outside)
        heat_loss_window = U_WINDOW * WINDOW_AREA * (T_room - T_outside)
        heat_loss_roof = U_ROOF * ROOF_AREA * (T_room - T_outside)
        heat_loss_ground = U_GROUND * GROUND_AREA * (T_room - T_outside)

        total_heat_loss = heat_loss_walls + heat_loss_door + heat_loss_window + heat_loss_roof + heat_loss_ground

        power_grzejnik = pi.update(T_sp, T_room)
        q = power_grzejnik - total_heat_loss
        dT = q/ TOTAL_C
        print(power_grzejnik)
        T_room += dT

    return time_array, temp_array



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
app.title = "Symulacja ogrzewania"

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Symulacja ogrzewania pokoju", className="text-center text-primary mb-4"),
                width=12)
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("Parametry", className="text-primary"),
                dbc.Label("kp:"),
                dcc.Slider(
                    id='input-kp',
                    min=0.0001,
                    max=1,
                    step=0.0001,
                    value=0.5,
                    marks={i / 10: str(i / 10) for i in range(0, 11)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                dbc.Label("Ti [s]:"),
                dcc.Slider(
                    id='input-ti',
                    min=0.1,
                    max=100,
                    step=0.1,
                    value=60,
                    marks={i: str(i) for i in range(0, 101, 10)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                dbc.Label("Tp [s]:"),
                dcc.Slider(
                    id='input-tp',
                    min=0.1,
                    max=5,
                    step=None,
                    value=1.0,
                    marks={
                        0.1: '1/10',
                        0.5: '5/10',
                        1: '1',
                        2: '2',
                        5: '5'
                    },
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
                dbc.Label("Temperatura zadana (°C):"),
                dbc.Input(
                    id='input-setpoint',
                    type='number',
                    value=23.0,
                    step=0.5
                ),
                dbc.Label("Temperatura na zewnątrz (°C):"),
                dbc.Input(
                    id='input-outside-temp',
                    type='number',
                    value=10.0,
                    step=0.5
                ),
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
        Input('input-tp', 'value'),
        Input('input-setpoint', 'value'),
        Input('input-outside-temp', 'value')
    ]
)
def update_figure(kp, ti, tp, setpoint, outside_temp):
    kp = kp if kp is not None else 100.0
    Ti = ti if ti is not None else 75.0
    Tp = tp if tp is not None else 1.0
    T_sp = setpoint if setpoint is not None else 25.0
    T_outside = outside_temp if outside_temp is not None else 15.0
    max_power = 2000.0

    time_array, temp_array = simulate_2h(
        kp, Ti, T_sp, Tp=Tp, T_outside=T_outside, max_power=max_power)
    temp_array = [round(temp, 2) for temp in temp_array]
    trace_temp = go.Scatter(
        x=time_array,
        y=temp_array,
        mode='lines',
        name='Temperatura (°C)',
        line=dict(color='red'),
        hovertemplate='Czas: %{x:.1f} min<br>Temperatura: %{y:.0f} °C<extra></extra>'
    )

    # Trace for the setpoint
    trace_setpoint = go.Scatter(
        x=time_array,
        y=[T_sp] * len(time_array),  # Horizontal line at setpoint temperature
        mode='lines',
        name='Temperatura zadana (°C)',
        line=dict(color='blue', dash='dash'),
        hovertemplate='Czas: %{x:.1f} min<br>Setpoint: %{y:.0f} °C<extra></extra>'
    )

    # Create the figure
    fig_temp = go.Figure(data=[trace_temp, trace_setpoint], layout=go.Layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Temperatura (°C)')
    ))
    return fig_temp


if __name__ == '__main__':
    app.run_server(debug=True)
