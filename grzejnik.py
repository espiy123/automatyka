import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import numpy as np


class PI:
    def __init__(self, kp, Ti, Tp, u_min, u_max):
        self.kp = kp
        self.Ti = Ti
        self.Tp = Tp
        self.u_min = u_min
        self.u_max = u_max
        self.u_prev = 0.0
        self.e_prev = 0.0
        self.delta_u = 0

    def reset(self):
        self.u_prev = 0.0
        self.e_prev = 0.0

    def update(self, setpoint, measurement):
        e = setpoint - measurement
        delta_e = e - self.e_prev

        delta_u = self.kp * (delta_e + (self.Tp / self.Ti) * e)
        self.delta_u = delta_u
        u = self.u_prev + delta_u

        u = np.clip(u, self.u_min, self.u_max)

        self.e_prev = e
        self.u_prev = u

        return u


# Funkcja Symulacji
def simulate_2h(kp, Ti, setpoint, Tp, T_init=20.0, T_outside=15.0):
    # Właściwości fizyczne i stałe
    VOLUME = 4.0 * 4.0 * 2.5  # m³
    AIR_DENSITY = 1.2  # kg/m³
    AIR_CAPACITY = 1005.0  # J/(kg·°C)
    MASS = VOLUME * AIR_DENSITY
    C = MASS * AIR_CAPACITY
    max_power = 5000.0


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

    SIM_TIME = int((2 * 3600) / Tp)
    pid = PI(kp=kp, Ti=Ti, Tp=Tp, u_min=0, u_max=max_power)
    pid.reset()
    time_array = []
    temp_array = []
    power_array = []
    heat_loss_array = []
    T_room = T_init

    for t in range(SIM_TIME):
        current_time_min = t * Tp / 60  # Konwersja na minuty
        time_array.append(current_time_min)
        temp_array.append(T_room)

        # Obliczanie strat ciepła
        heat_loss_walls = U_WALL * WALL_AREA * (T_room - T_outside)
        heat_loss_door = U_DOOR * DOOR_AREA * (T_room - T_outside)
        heat_loss_window = U_WINDOW * WINDOW_AREA * (T_room - T_outside)
        heat_loss_roof = U_ROOF * ROOF_AREA * (T_room - T_outside)
        heat_loss_ground = U_GROUND * GROUND_AREA * (T_room - T_outside)

        total_heat_loss = (heat_loss_walls + heat_loss_door + heat_loss_window + heat_loss_roof)*0.5
        heat_loss_array.append(total_heat_loss)

        # Aktualizacja mocy grzejnika uwzględniająca powierzchnię grzejnika
        P_grzejnik = pid.update(setpoint, T_room)
        P_grzejnik_total = np.clip(P_grzejnik, 0, max_power)  # Ograniczenie do u_max
        power_array.append(P_grzejnik_total)

        # Aktualizacja temperatury w pomieszczeniu
        q = P_grzejnik_total  # Energia dodana przez grzejnik
        dT = (q - total_heat_loss * Tp) / C
        T_room += dT

    return time_array, temp_array, power_array, heat_loss_array


# Inicjalizacja aplikacji Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
app.title = "Symulacja ogrzewania"

# Lista możliwych wartości Tp
tp_values = [0.1, 0.5, 1, 2, 5]

# Domyślna powierzchnia grzejnika
DEFAULT_A_HEATER = 1.5  # m²

# Układ aplikacji
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
                    value=0.8,
                    marks={i / 10: f"{i / 10}" for i in range(0, 11)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),

                dbc.Label("Ti [s]:"),
                dcc.Slider(
                    id='input-ti',
                    min=0.1,
                    max=10,
                    step=0.1,
                    value=5,
                    marks={i: f"{i}" for i in range(0, 11)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),

                dbc.Label("Tp [s]:"),
                dcc.Slider(
                    id='input-tp',
                    min=0,
                    max=len(tp_values) - 1,
                    step=1,
                    value=2,  # Domyślna wartość odpowiadająca Tp=1
                    marks={i: f"{tp_values[i]} s" for i in range(len(tp_values))},
                    tooltip={"placement": "bottom", "always_visible": True}
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
                    value=15.0,
                    step=0.5
                ),

            ], className="border p-3 shadow-sm")

        ], width=3),
        dbc.Col([
            dcc.Graph(id='graph-temperature'),
            dcc.Graph(id='graph-power')
        ], width=9)
    ])
], fluid=True)


# Callback do aktualizacji wykresów
@app.callback(
    [
        Output('graph-temperature', 'figure'),
        Output('graph-power', 'figure')
    ],
    [
        Input('input-kp', 'value'),
        Input('input-ti', 'value'),
        Input('input-tp', 'value'),
        Input('input-setpoint', 'value'),
        Input('input-outside-temp', 'value')
    ]
)
def update_figures(kp, ti, tp_index, setpoint, outside_temp):
    # Mapowanie indeksu Tp na rzeczywistą wartość Tp
    Tp = tp_values[tp_index] if 0 <= tp_index < len(tp_values) else 1.0

    # Domyślne wartości, jeśli dane wejściowe są puste
    kp = kp if kp is not None else 0.8
    Ti = ti if ti is not None else 5.0
    setpoint = setpoint if setpoint is not None else 23.0
    T_outside = outside_temp if outside_temp is not None else 15.0

    # Stała powierzchnia grzejnika
    A_heater = DEFAULT_A_HEATER

    # Uruchomienie symulacji
    time_array, temp_array, power_array, heat_loss_array = simulate_2h(
        kp, Ti, setpoint, Tp=Tp, T_outside=T_outside)

    # Zaokrąglenie wartości temperatury i mocy dla lepszej czytelności
    temp_array = [round(temp, 2) for temp in temp_array]
    power_array = [round(power, 2) for power in power_array]
    heat_loss_array = [round(heat, 2) for heat in heat_loss_array]

    # Tworzenie śladu dla temperatury
    trace_temp = go.Scatter(
        x=time_array,
        y=temp_array,
        mode='lines',
        name='Temperatura (°C)',
        line=dict(color='red'),
        hovertemplate='Czas: %{x:.1f} min<br>Temperatura: %{y:.1f} °C<extra></extra>'
    )

    # Tworzenie śladu dla temperatury zadanej
    trace_setpoint = go.Scatter(
        x=time_array,
        y=[setpoint] * len(time_array),
        mode='lines',
        name='Temperatura zadana (°C)',
        line=dict(color='blue', dash='dash'),
        hovertemplate='Czas: %{x:.1f} min<br>Setpoint: %{y:.1f} °C<extra></extra>'
    )

    # Tworzenie śladu dla mocy grzejnika
    trace_power = go.Scatter(
        x=time_array,
        y=power_array,
        mode='lines',
        name='Moc grzejnika (W)',
        line=dict(color='green'),
        hovertemplate='Czas: %{x:.1f} min<br>Moc: %{y:.1f} W<extra></extra>'
    )

    # Tworzenie śladu dla strat ciepła
    trace_heat_loss = go.Scatter(
        x=time_array,
        y=heat_loss_array,
        mode='lines',
        name='Strata ciepła (W)',
        line=dict(color='orange'),
        hovertemplate='Czas: %{x:.1f} min<br>Strata ciepła: %{y:.1f} W<extra></extra>'
    )

    # Konfiguracja wykresu temperatury
    fig_temp = go.Figure()
    fig_temp.add_trace(trace_temp)
    fig_temp.add_trace(trace_setpoint)
    fig_temp.update_layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Temperatura (°C)', side='left'),
        legend=dict(x=0.01, y=0.99),
        title='Symulacja ogrzewania z regulatorem PI - Temperatura',
    )

    # Konfiguracja wykresu mocy grzejnika i strat ciepła
    fig_power = go.Figure()
    fig_power.add_trace(trace_power)
    fig_power.add_trace(trace_heat_loss)
    fig_power.update_layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Moc/Strata (W)'),
        legend=dict(x=0.01, y=0.99),
        title='Symulacja ogrzewania z regulatorem PI - Moc Grzejnika i Strata Ciepła',
    )

    return fig_temp, fig_power


# Uruchomienie aplikacji Dash
if __name__ == '__main__':
    app.run_server(debug=True)
