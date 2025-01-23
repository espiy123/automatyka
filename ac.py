import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# Klasa PID
class PID:
    def __init__(self, Kp, Ki, Kd, setpoint=25.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint

        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, current_value, dt):
        error = self.setpoint - current_value
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt if dt > 0 else 0.0

        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative

        self.previous_error = error

        return output

# Funkcja symulacji
def simulate_aquarium(pid, initial_temp=20.0, ambient_temp=20.0,
                      heater_power=300.0, cooling_coefficient=5.0,
                      duration=3600, dt=1,
                      length_cm=200, width_cm=80, height_cm=60):
    """
    Symuluje proces regulacji temperatury w akwarium przez określony czas.

    :param pid: Instancja regulatora PID
    :param initial_temp: Początkowa temperatura akwarium (°C)
    :param ambient_temp: Temperatura otoczenia (°C)
    :param heater_power: Moc grzałki (W)
    :param cooling_coefficient: Współczynnik chłodzenia (W/°C)
    :param duration: Czas symulacji w sekundach (3600 sekund = 1 godzina)
    :param dt: Krok czasowy symulacji w sekundach
    :param length_cm: Długość akwarium w cm
    :param width_cm: Szerokość akwarium w cm
    :param height_cm: Wysokość akwarium w cm
    :return: Listy czasu (minuty) i temperatury (°C)
    """
    # Obliczenia objętości i masy cieplnej
    volume_cm3 = length_cm * width_cm * height_cm  # cm³
    volume_liters = volume_cm3 / 1000  # 1 litr = 1000 cm³
    mass_water = volume_liters  # kg (gęstość wody ≈ 1 kg/L)
    specific_heat_water = 4186  # J/(kg°C)
    thermal_mass = mass_water * specific_heat_water  # J/°C

    temperature = initial_temp
    temperatures = [temperature]
    times = [0]
    heater = 0.0

    for t in range(1, duration + 1, dt):
        heater = pid.update(temperature, dt)
        heater = max(0.0, min(heater, heater_power))

        # Obliczenie chłodzenia
        cooling = cooling_coefficient * (temperature - ambient_temp)  # W

        # Zmiana temperatury
        delta_temp = (heater - cooling) * dt / thermal_mass  # °C
        temperature += delta_temp

        temperatures.append(temperature)
        times.append(t)

    # Konwersja czasu z sekund na minuty
    times_in_minutes = [t / 60 for t in times]

    return times_in_minutes, temperatures

# Inicjalizacja aplikacji Dash
app = dash.Dash(__name__)
app.title = "Symulacja Regulacji PID w Akwarium"

# Układ aplikacji
app.layout = html.Div([
    html.H1("Symulacja Regulacji Temperatury w Akwarium za pomocą PID", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label('Kp'),
            dcc.Slider(
                id='Kp-slider',
                min=0,
                max=100,
                step=0.1,
                value=30.0,
                marks={i: str(i) for i in range(0, 101, 10)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Div(id='Kp-output', style={'textAlign': 'center'})
        ], style={'width': '24%', 'display': 'inline-block', 'padding': '20px'}),

        html.Div([
            html.Label('Ki'),
            dcc.Slider(
                id='Ki-slider',
                min=0,
                max=10,
                step=0.1,
                value=0.2,
                marks={i: str(i) for i in range(0, 11, 1)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Div(id='Ki-output', style={'textAlign': 'center'})
        ], style={'width': '24%', 'display': 'inline-block', 'padding': '20px'}),

        html.Div([
            html.Label('Kd'),
            dcc.Slider(
                id='Kd-slider',
                min=0,
                max=50,
                step=0.1,
                value=10.0,
                marks={i: str(i) for i in range(0, 51, 5)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Div(id='Kd-output', style={'textAlign': 'center'})
        ], style={'width': '24%', 'display': 'inline-block', 'padding': '20px'}),

        html.Div([
            html.Label('Moc grzałki (W)'),
            dcc.Slider(
                id='heater-slider',
                min=100,
                max=500,
                step=10,
                value=300.0,
                marks={i: str(i) for i in range(100, 501, 50)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Div(id='heater-output', style={'textAlign': 'center'})
        ], style={'width': '24%', 'display': 'inline-block', 'padding': '20px'}),
    ], style={'display': 'flex', 'justifyContent': 'center'}),

    dcc.Graph(id='temperature-graph')
])

# Callback do aktualizacji wartości suwaków
@app.callback(
    [Output('Kp-output', 'children'),
     Output('Ki-output', 'children'),
     Output('Kd-output', 'children'),
     Output('heater-output', 'children')],
    [Input('Kp-slider', 'value'),
     Input('Ki-slider', 'value'),
     Input('Kd-slider', 'value'),
     Input('heater-slider', 'value')]
)
def update_slider_output(Kp, Ki, Kd, heater_power):
    return f'Kp: {Kp}', f'Ki: {Ki}', f'Kd: {Kd}', f'Moc grzałki: {heater_power} W'

# Callback do aktualizacji wykresu na podstawie suwaków
@app.callback(
    Output('temperature-graph', 'figure'),
    [Input('Kp-slider', 'value'),
     Input('Ki-slider', 'value'),
     Input('Kd-slider', 'value'),
     Input('heater-slider', 'value')]
)
def update_graph(Kp, Ki, Kd, heater_power):
    setpoint = 25.0  # Żądana temperatura
    pid = PID(Kp, Ki, Kd, setpoint)
    times, temperatures = simulate_aquarium(pid, heater_power=heater_power)

    # Tworzenie wykresu
    fig = go.Figure()

    # Wykres temperatury
    fig.add_trace(go.Scatter(
        x=times,
        y=temperatures,
        mode='lines',
        name='Temperatura akwarium',
        line=dict(color='blue')
    ))

    # Linia setpoint
    fig.add_trace(go.Scatter(
        x=[0, times[-1]],
        y=[setpoint, setpoint],
        mode='lines',
        name='Setpoint',
        line=dict(color='red', dash='dash')
    ))

    # Konfiguracja layoutu
    fig.update_layout(
        title='Symulacja Regulacji Temperatury w Akwarium za pomocą PID (1 godzina)',
        xaxis_title='Czas (minuty)',
        yaxis_title='Temperatura (°C)',
        legend=dict(x=0.01, y=0.99),
        template='plotly_white',
        height=600
    )

    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)

    return fig

# Uruchomienie serwera
if __name__ == '__main__':
    app.run_server(debug=True)
