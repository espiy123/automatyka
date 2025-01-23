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

        self.delta_u = self.kp * (delta_e + (self.Tp / self.Ti) * e)
        u = self.u_prev + self.delta_u

        u = np.clip(u, 0, 1)
        self.e_prev = e
        self.u_prev = u
        return u

def simulate_2h(kp, Ti, setpoint, Tp, T_init=20.0, T_outside=15.0):
    VOLUME = 0.112 # 0.8 x 0.35 x 0.4
    water_density = 997  # kg/m³
    water_CAPACITY = 4189.9  # J/(kg·°C)
    MASS = VOLUME * water_density
    max_power = 200.0

    SIM_TIME = int((4 * 3600) / Tp)
    pid = PI(kp=kp, Ti=Ti, Tp=Tp, u_min=0, u_max=max_power)
    pid.reset()
    time_array = []
    temp_array = []
    power_array = []
    heat_loss_array = []
    T_water = T_init

    for t in range(SIM_TIME):
        current_time_min = t * Tp / 60  # Konwersja na minuty
        time_array.append(current_time_min)
        temp_array.append(T_water)
        Q = pid.update(setpoint,T_water)*max_power

        Qloss = 1*1.68*(T_water - T_outside)
        dT = ((Q-Qloss)/(MASS*water_CAPACITY))*Tp

        T_water += dT
        power_array.append(Q)
        heat_loss_array.append(Qloss)
    return time_array, temp_array, power_array, heat_loss_array


# Inicjalizacja aplikacji Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
app.title = "Symulacja ogrzewania"

# Lista możliwych wartości Tp
tp_values = [0.1, 0.5, 1, 2, 5]


# Układ aplikacji
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Symulacja akwarium", className="text-center text-primary mb-4"),
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
                    min=0,
                    max=50,
                    step=0.1,
                    value=20,
                    marks={i: f"{i}" for i in range(0, 51,5)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),

                dbc.Label("Tp [s]:"),
                dcc.Slider(
                    id='input-tp',
                    min=0,
                    max=len(tp_values) - 1,
                    step=1,
                    value=2,
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

                dbc.Label("Temperatura powietrza (°C):"),
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
        hovertemplate='Czas: %{x:.1f} min<br>Temperatura: %{y:.0f} °C<extra></extra>'
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
        name='Moc grzałki (W)',
        line=dict(color='green'),
        hovertemplate='Czas: %{x:.1f} min<br>Moc: %{y:.2f} W<extra></extra>'
    )

    # Tworzenie śladu dla strat ciepła
    trace_heat_loss = go.Scatter(
        x=time_array,
        y=heat_loss_array,
        mode='lines',
        name='Strata ciepła (J)',
        line=dict(color='orange'),
        hovertemplate='Czas: %{x:.1f} min<br>Energia: %{y:.2f} J<extra></extra>'
    )

    fig_temp = go.Figure()
    fig_temp.add_trace(trace_temp)
    fig_temp.add_trace(trace_setpoint)
    fig_temp.update_layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Temperatura (°C)', side='left'),
        legend=dict(x=0.01, y=0.99),
        title='Symulacja ogrzewania',
    )

    fig_power = go.Figure()
    fig_power.add_trace(trace_power)
    fig_power.add_trace(trace_heat_loss)
    fig_power.update_layout(
        xaxis=dict(title='Czas (minuty)'),
        yaxis=dict(title='Moc/Strata (W)'),
        legend=dict(x=0.01, y=0.99),
        title='Moc grzałki i strata ciepła',
    )

    return fig_temp, fig_power


# Uruchomienie aplikacji Dash
if __name__ == '__main__':
    app.run_server(debug=True)
