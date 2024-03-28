import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

data = pd.read_csv('spotify-2023.csv', encoding='ISO-8859-1')
artist_counts = data['artist(s)_name'].str.split(', ').explode().value_counts().reset_index()
artist_counts.columns = ['artist', 'count']
total_tracks = len(data)

average_values = data[['danceability_%', 'valence_%', 'energy_%', 'acousticness_%', 'instrumentalness_%', 'liveness_%', 'speechiness_%']].mean()

x_attribute = data.columns[8]
y_attribute = data.columns[8]
color_attribute = data.columns[8]
size_attribute = data.columns[8]

x_dropdown = [dict(label=attribute, method='update', args=[{'x': [data[attribute]]}, {'xaxis.title.text': attribute}, {'labels': {x_attribute: attribute}}]) for attribute in data.columns]
y_dropdown = [dict(label=attribute, method='update', args=[{'y': [data[attribute]]}, {'yaxis.title.text': attribute}, {'labels': {y_attribute: attribute}}]) for attribute in data.columns]
color_dropdown = [dict(label=attribute, method='update', args=[{'marker.color': [data[attribute]]}, {'coloraxis.colorbar.title.text': attribute}, {'labels': {color_attribute: attribute}}]) for attribute in data.columns]
size_dropdown = [dict(label=attribute, method='update', args=[{'marker.size': [data[attribute]]}, {'marker.size.title.text': attribute}, {'labels': {size_attribute: attribute}}]) for attribute in data.columns]

artist_dropdown = dcc.Dropdown(id='artist-dropdown', options=[{'label': artist, 'value': artist} for artist in data['artist(s)_name'].unique()], multi=True, placeholder='Select artist(s)', style={'width': '50%'})

def create_scatter_plot(x_attr, y_attr, color_attr, size_attr, selected_artists=None, stream_range=None, top_percent=None):
    global x_attribute, y_attribute, color_attribute, size_attribute
    x_attribute = x_attr
    y_attribute = y_attr
    color_attribute = color_attr
    size_attribute = size_attr

    filtered_data = data[data['artist(s)_name'].apply(lambda artists: any(artist in artists for artist in selected_artists))] if selected_artists else data

    if stream_range:
        filtered_data = filtered_data[(filtered_data['streams'] >= stream_range[0]) & (filtered_data['streams'] <= stream_range[1])]

    if top_percent:
        top_n = int((top_percent / 100) * len(filtered_data))
        filtered_data = filtered_data.nlargest(top_n, 'streams')

    fig = px.scatter(filtered_data, x=x_attr, y=y_attr, color=color_attr, size=size_attr, labels={col: col for col in data.columns}, hover_data={'track_name': True, 'artist(s)_name': True})

    fig.update_layout(updatemenus=[
        dict(type='dropdown', direction='down', x=0.1, y=1.15, showactive=True, buttons=x_dropdown),
        dict(type='dropdown', direction='down', x=0.25, y=1.15, showactive=True, buttons=y_dropdown),
        dict(type='dropdown', direction='down', x=0.4, y=1.15, showactive=True, buttons=color_dropdown),
        dict(type='dropdown', direction='down', x=0.55, y=1.15, showactive=True, buttons=size_dropdown),
    ])

    fig.update_layout(xaxis_title_text=x_attr, yaxis_title_text=y_attr)
    return fig

def create_radar_chart(selected_song=None, top_percent=None):
    if selected_song is None or selected_song == 'Average':
        if top_percent:
            top_n = int((top_percent / 100) * len(data))
            top_data = data.nlargest(top_n, 'streams')
            values = top_data[['danceability_%', 'valence_%', 'energy_%', 'acousticness_%', 'instrumentalness_%', 'liveness_%', 'speechiness_%']].mean().values
            title = f'Average Audio Features for Top {top_percent}% of Streams'
        else:
            values = average_values.values
            title = 'Average Audio Features'
    else:
        selected_song_data = data[data['track_name'] == selected_song]

        if top_percent:
            top_n = int((top_percent / 100) * len(selected_song_data))
            selected_song_data = selected_song_data.nlargest(top_n, 'streams')

        values = selected_song_data[['danceability_%', 'valence_%', 'energy_%', 'acousticness_%', 'instrumentalness_%', 'liveness_%', 'speechiness_%']].iloc[0].values
        title = f'Audio Features for {selected_song}'

    categories = average_values.index
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name='Selected Song'))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, title=title)
    return fig

def create_heatmap(top_percent=None):
    numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns
    numeric_data = data[numeric_columns]

    if top_percent:
        top_n = int((top_percent / 100) * len(numeric_data))
        numeric_data = numeric_data.nlargest(top_n, 'streams')

    correlation_matrix = numeric_data.corr()

    fig = go.Figure()

    fig.add_trace(go.Heatmap(x=correlation_matrix.index, y=correlation_matrix.columns, z=correlation_matrix.values, colorscale='Viridis'))

    fig.update_layout(title='Correlation Heatmap', xaxis=dict(title='Audio Features'), yaxis=dict(title='Audio Features'))
    return fig

def create_artist_bar_chart(top_n=20):
    if top_n:
        top_artists_filtered = artist_counts.head(top_n)
    else:
        top_artists_filtered = artist_counts

    unique_tracks_top_n = set()

    for artist in top_artists_filtered['artist']:
        collab_tracks = data[data['artist(s)_name'].apply(lambda artists: artist in artists and len(artists) > 1)]
        unique_tracks_top_n.update(collab_tracks['track_name'].unique())

    total_tracks_top_n = len(unique_tracks_top_n)
    percentage = (total_tracks_top_n / total_tracks) * 100

    fig = px.bar(top_artists_filtered, x='count', y='artist', orientation='h', labels={'count': 'Number of Tracks', 'artist': 'Artist'}, title=f'Top Artists by Track Count ({percentage:.2f}% of Total Tracks)')
    return fig

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Scatter Plot', children=[
            html.Div([
                artist_dropdown,
                html.Label('Stream Range:'),
                dcc.RangeSlider(id='stream-range-slider', min=data['streams'].min(), max=data['streams'].max(), step=100000000, marks={i: {'label': f'{i // 1000000}M'} for i in range(data['streams'].min(), data['streams'].max() + 1, 100000000)}),
                html.Label('Top N%:'),
                dcc.Input(id='scatter-top-percent-input', type='number', placeholder='Top N%', style={'width': '50%'}),
                dcc.Graph(id='scatter-plot', figure=create_scatter_plot(x_attribute, y_attribute, color_attribute, size_attribute), style={'height': '80vh'}),
            ]),
        ]),
        dcc.Tab(label='Radar Chart', children=[
            html.Div([
                dcc.Dropdown(id='song-dropdown', options=[{'label': 'Average', 'value': 'Average'}] + [{'label': song, 'value': song} for song in data['track_name'].unique()], value='Average', placeholder='Select a song'),
                html.Label('Top N%:'),
                dcc.Input(id='radar-top-percent-input', type='number', placeholder='Top N%', style={'width': '50%'}),
                dcc.Graph(id='radar-chart', figure=create_radar_chart(), style={'height': '80vh'}),
            ]),
        ]),
        dcc.Tab(label='Correlation Heatmap', children=[
            html.Div([
                html.Label('Top N%:'),
                dcc.Input(id='heatmap-top-percent-input', type='number', placeholder='Top N%', style={'width': '50%'}),
                dcc.Graph(id='heatmap', figure=create_heatmap(), style={'height': '80vh'}),
            ]),
        ]),
        dcc.Tab(label='Top Artists Bar Chart', children=[
            html.Div([
                html.Label('Top N Artists:'),
                dcc.Input(id='artist-top-n-input', type='number', placeholder='Enter the number of artists', style={'width': '50%'}),
                dcc.Graph(id='artist-bar-chart', figure=create_artist_bar_chart(), style={'height': '80vh'}),
            ]),
        ]),
    ]),
])

@app.callback(
    Output('scatter-plot', 'figure'),
    [Input('artist-dropdown', 'value'),
     Input('stream-range-slider', 'value'),
     Input('scatter-top-percent-input', 'value')]
)
def update_scatter_plot(selected_artists, stream_range, top_percent):
    x_attr = x_attribute
    y_attr = y_attribute

    fig = create_scatter_plot(x_attr, y_attr, color_attribute, size_attribute, selected_artists, stream_range, top_percent)
    fig.update_layout(xaxis_title_text=x_attr, yaxis_title_text=y_attr)
    return fig

@app.callback(
    Output('radar-chart', 'figure'),
    [Input('song-dropdown', 'value'),
     Input('radar-top-percent-input', 'value')]
)
def update_radar_chart(selected_song, top_percent):
    return create_radar_chart(selected_song, top_percent)

@app.callback(
    Output('heatmap', 'figure'),
    [Input('heatmap-top-percent-input', 'value')]
)
def update_heatmap(top_percent):
    return create_heatmap(top_percent)

@app.callback(
    Output('artist-bar-chart', 'figure'),
    [Input('artist-top-n-input', 'value')]
)
def update_artist_bar_chart(top_n):
    return create_artist_bar_chart(top_n)

if __name__ == '__main__':
    app.run_server(debug=True)
