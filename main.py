from dash import Dash, dcc, html, dash_table, Input, Output, State, callback

import base64
import datetime
import io

import pandas as pd



app = Dash(__name__)

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-data-upload'),
])


def open(df):
    df = df
    columnas_tabla = ['Fecha', 'Hora', 'pH bocatoma (ph)', 'pH salida (pH)', 'Turbiedad (NTU)',
                      'Cloro residual (PPM)', 'QE1 (L/s)', 'QE2 (L/s)',
                      'QS1 (L/s)', 'QS2 (L/s)', 'Sensor de nivel (m)', 'QTE (L/s)', 'QTS (L/s)', 'V horario E',
                      'V horario S',
                      'V regulacion', 'V real']

    df.columns = ['columna 1', 'pH bocatoma (ph)', 'pH salida (pH)', 'Turbiedad (NTU)', 'Cloro residual (PPM)',
                  'QE1 (L/s)', 'QE2 (L/s)',
                  'QS1 (L/s)', 'QS2 (L/s)', 'Sensor de nivel (m)']

    # Ahora puedes dividir la primera columna (que ahora se llama 'columna1')
    df[['Fecha', 'Hora']] = df['columna 1'].str.split(' ', expand=True)

    # eliminar la columna original
    df = df.drop(columns=['columna 1'])

    dfnuevo = df.iloc[:, :-2]
    dfnuevo = dfnuevo.apply(pd.to_numeric)
    dfnuevo = dfnuevo / 100

    df[dfnuevo.columns] = dfnuevo

    # Reordena las columnas para que 'fecha' y 'hora' sean las dos primeras
    df = df[['Fecha', 'Hora'] + [c for c in df.columns if c not in ['Fecha', 'Hora']]]

    # Convierte la fecha al formato deseado
    df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%d/%m/%Y')
    df['Fecha'] = df['Fecha'].astype(str)

    # Asegúrate de que la hora esté en el formato correcto
    df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M:%S').dt.time
    df['Hora'] = df['Hora'].astype(str)

    df['QTE (L/s)'] = df['QE1 (L/s)'] + df['QE2 (L/s)']
    df['QTE (L/s)'] = df['QTE (L/s)'].round(2)
    df['QTS (L/s)'] = df['QS1 (L/s)'] + df['QS2 (L/s)']
    df['QTS (L/s)'] = df['QTS (L/s)'].round(2)
    # Agrega una nueva columna que es la suma del dato actual y el dato anterior en 'Macro 1+2'
    df['V horario E'] = df['QTE (L/s)'] + df['QTE (L/s)'].shift(1)
    df['V horario E'] = df['V horario E'].fillna(df['QTE (L/s)'] * 7200 / 1000)

    # Agrega una nueva columna que es la suma del dato actual y el dato anterior en 'Macro 3+4'
    df['V horario S'] = df['QTS (L/s)'] + df['QTS (L/s)'].shift(1)
    df['V horario S'] = df['V horario S'].fillna(df['QTS (L/s)'] * 7200 / 1000)

    # Multiplica todas las filas excepto la primera por 3,6 en 'Macro 1+2 acumulado'
    df.loc[1:, 'V horario E'] *= 3.6
    df['V horario E'] = df['V horario E'].round(2)

    # Multiplica todas las filas excepto la primera por 3,6 en 'Macro 3+4 acumulado'
    df.loc[1:, 'V horario S'] *= 3.6
    df['V horario S'] = df['V horario S'].round(2)

    # Crea una nueva columna que es la suma del dato de la fila anterior y la resta de 'Macro 1+2 acumulado' y 'Macro 3+4 acumulado'
    df['V regulacion'] = df['V horario E'] - df['V horario S']
    df['V real'] = df['V regulacion']
    df['V regulacion'] = df['V regulacion'].shift(1) + df['V regulacion']
    df['V regulacion'] = df['V regulacion'].fillna(0)
    df['V regulacion'] = df['V regulacion'].round(2)
    df['V real'] = df['V real'].shift(1) + df['V real']
    df['V real'] = df['V real'].fillna(0)
    df['V real'] = df['V real'].round(2)
    return df



def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            df = open(df)
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
            df = open(df)
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return html.Div([
        html.H5("Variables acueducto el retiro"),
        html.H6(datetime.datetime.now()),

        dash_table.DataTable(
            df.to_dict('records'),
            [{'name': i, 'id': i} for i in df.columns],
            style_table={'height': '800px', 'overflowY': 'auto', 'overflowX': 'auto'},
            style_header={'border': '1px solid black'},
            style_cell={'border': '1px solid grey', 'textAlign': 'left'},
            column_selectable='single',
            selected_columns=[],
            selected_rows=[],
            page_action="native",
            page_current=0,
            page_size=100,
        ),

        html.Hr(),  # horizontal line

        # For debugging, display the raw contents provided by the web browser
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...', style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-all'
        })
    ])

@callback(Output('output-data-upload', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children

if __name__ == '__main__':
    app.run(debug=True)
