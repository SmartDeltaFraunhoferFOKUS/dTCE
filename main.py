# import logging
# import os
import pickle
import subprocess
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Output, Input, State, callback_context
from plotly.subplots import make_subplots

from CoverageAnalyzer import CoverageAnalyzer
from utils import *

# used for the GitHub API. Please bring your own.
load_dotenv("./.env")
github_token = os.environ.get("GITHUB_TOKEN")


def create_dash_app():
    # external CSS stylesheets
    external_stylesheets = [
        'https://codepen.io/chriddyp/pen/bWLwgP.css',
        {
            'href': 'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
            'rel': 'stylesheet',
            'integrity': 'sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO',
            'crossorigin': 'anonymous'
        }
    ]
    app = Dash(__name__, external_stylesheets=external_stylesheets)
    app.layout = html.Div(
        style={
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center',
            'overflow-y': 'auto'
        },
        children=[
            html.H1("Coverage Analyzer"),

            # Input field for GitHub repository URL
            html.Label("Enter GitHub Repository URL:"),
            dcc.Input(
                id='github-input',
                type='text',
                placeholder='https://github.com/your_username/your_repository',
                value='https://github.com/LeonardFiedrowicz/MavenJacocoExample',
                style={'width': '40%', 'margin-top': '5px', 'text-align': 'center'}
            ),

            # File selector to select a folder
            html.Label("Enter Folder Path:"),
            dcc.Input(
                id='folder-input',
                value='C:\\Coverage',
                style={'width': '40%', 'margin-top': '5px', 'text-align': 'center'}
            ),

            # Download button
            html.Button('Download', id='download-button', style={'margin-top': '20px'}),

            # Div to display the result or the analysis page
            html.Div(id='module-selection', style={'margin-top': '20px', 'width': '40%'}),
            html.Div(id='page-content', style={'margin-top': '20px', 'width': '100%'})
        ]
    )

    # Callback to display analysis page when Download button is clicked
    @app.callback(
        Output('module-selection', 'children'),
        Input('download-button', 'n_clicks'),
        State('github-input', 'value'),
        State('folder-input', 'value'),
        prevent_initial_call=True
    )
    def display_analysis_page(n_clicks, url, path):
        if n_clicks is None:
            return ''
        repo_name = url.split("/")[-1]
        if not os.path.exists(path):
            os.makedirs(path)
        os.chdir(path)
        repo_path = path + "\\" + repo_name
        logging.info("Cloning repository into the folder\n\t\t" + repo_path)
        if os.path.exists(repo_path):
            logging.info("Using existing download of the repository and updating it")
            os.chdir(repo_path)
            subprocess.run("git fetch origin")
        else:
            subprocess.run("git clone " + url)
            logging.info("Cloned repository")

        # search for module
        dir_list = list()
        for directory in find_pom(repo_path)[:10]:
            dir_list.append({'label': directory, 'value': directory})
        logging.info(dir_list)

        return html.Div(
            children=[
                html.Label("Select Module:"),
                dcc.Dropdown(
                    id='module-selector',
                    options=dir_list,
                    value=None,
                    style={'width': '100%', 'margin-top': '5px'}
                ),
                html.Button('Analyze', id='analyze-button', style={'margin-top': '20px'}),
                html.Button('Go Back', id='go-back-button', style={'margin-top': '20px'})
            ])

    # Callback to switch between the main page and the analysis page
    @app.callback(
        Output('page-content', 'children'),
        Input('go-back-button', 'n_clicks'),
        Input('analyze-button', 'n_clicks'),
        State('page-content', 'children'),
        State('github-input', 'value'),
        State('folder-input', 'value'),
        Input('module-selector', 'value'),
        prevent_initial_call=True
    )
    def switch_page(go_back_clicks, analyze_clicks, current_page, url, path, module_path):
        ctx = callback_context
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if button_id == 'go-back-button':
            return ''
        elif button_id == 'analyze-button':
            # Replace this with code to display analysis graphs
            repo_name = url.split("/")[-1]
            if not os.path.exists(path + "/cache/" + repo_name + "_coverage_data"):
                my_coverage = CoverageAnalyzer(github_token=github_token, url=url, path=path, module_path=module_path)
                my_coverage.get_coverage()
            return create_graphs(url, path)
    app.run_server(debug=False, threaded=True)


def create_graphs(url, path):
    repo_name = url.split("/")[-1]
    os.chdir(path + "/cache/")

    with open(repo_name + "_coverage_data", "rb") as file:
        coverage_data = pickle.load(file)
    with open(repo_name + "_total_uncovered_lines", "rb") as file:
        total_uncovered_lines = pickle.load(file)
    with open(repo_name + "_test_data", "rb") as file:
        test_data = pickle.load(file)
    with open(repo_name + "_total_lines_text", "rb") as file:
        total_lines_text = pickle.load(file)
    with open(repo_name + "_df_heatmap", "rb") as file:
        df_heatmap = pickle.load(file)
    with open(repo_name + "_heatmap_data", "rb") as file:
        heatmap_data = pickle.load(file)

    # prepare data
    df = pd.DataFrame.from_dict(coverage_data)

    coverage_length = len(coverage_data["covered"])
    coverage_data_percent = dict()
    total = [coverage_data["covered"][i] + coverage_data["missed"][i] for i in range(coverage_length)]
    coverage_data_percent["covered"] = [coverage_data["covered"][i] / total[i] * 100 for i in
                                        range(coverage_length)]
    coverage_data_percent["missed"] = [coverage_data["missed"][i] / total[i] * 100 for i in
                                       range(coverage_length)]
    coverage_data_percent["time"] = coverage_data["time"]
    df_percent = pd.DataFrame.from_dict(coverage_data_percent)

    df_uncovered_lines = pd.DataFrame.from_dict(total_uncovered_lines)
    df_uncovered_lines["time"] = df["time"][1:]

    df_test_data = pd.DataFrame.from_dict(test_data)
    df_test_data["time"] = df["time"]
    df_heatmap = df_heatmap[
        (~df_heatmap["file_name"].str.contains("/src/test/")) &
        (df_heatmap["file_name"].str.contains(".java"))]

    heatmap_modules, heatmap_files, line_covered_heatmap, line_uncovered_heatmap = heatmap_data
    heatmap_file_names = list()
    # line_covered_heatmap, line_uncovered_heatmap = heatmap_lines
    heatmap_covered = list()
    for file_name, file_lines in line_covered_heatmap.items():
        heatmap_covered.append(file_lines)
        heatmap_file_names.append(file_name.split("/")[-1][:-5])
    # transpose heatmap
    heatmap_covered = [list(i) for i in zip(*heatmap_covered)]

    heatmap_uncovered = list()
    for file_name, file_lines in line_uncovered_heatmap.items():
        print(len(file_lines))
        heatmap_uncovered.append(file_lines)
    # transpose heatmap
    heatmap_uncovered = [list(i) for i in zip(*heatmap_uncovered)]

    # prepare graphs
    fig_subplots = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=["Total Coverage", "Total Coverage in Percent", "New Line Coverage", "Line Coverage in Percent"]
        )
    fig_subplots.update_layout(
        autosize=True,
        # width=1000,
        height=1000,
        margin=dict(
            l=50,
            r=50,
            b=100,
            t=100,
            pad=4
        ),
    )
    # graph 1
    fig_subplots.add_trace(go.Scatter(x=df["time"], y=df["covered"], name="covered", mode="lines",
                                            line=dict(width=0.5, color="rgb(10, 200, 10)"), stackgroup="one", legendgroup="group1"), row=1, col=1)
    fig_subplots.add_trace(go.Scatter(x=df["time"], y=df["missed"], name="uncovered", mode="lines",
                                            line=dict(width=0.5, color="rgb(200, 10, 10)"), stackgroup="one", legendgroup="group2"), row=1, col=1)
    # graph 2
    fig_subplots.add_trace(
        go.Scatter(x=df_percent["time"], y=df_percent["covered"], name="covered", mode="lines",
                   line=dict(width=0.5, color="rgb(10, 200, 10)"), stackgroup="one", legendgroup="group1"), row=1, col=2)
    fig_subplots.add_trace(
        go.Scatter(x=df_percent["time"], y=df_percent["missed"], name="uncovered", mode="lines",
                   line=dict(width=0.5, color="rgb(200, 10, 10)"), stackgroup="one", legendgroup="group2"), row=1, col=2)
    # graph 3
    fig_subplots.add_trace(
        go.Scatter(x=df_uncovered_lines["time"], y=df_uncovered_lines["new_lines"], name="new lines", mode="lines",
                   line=dict(width=0.5, color="rgb(150, 150, 150)"), stackgroup="one", legendgroup="group1"), row=2, col=1)
    fig_subplots.add_trace(
        go.Scatter(x=df_uncovered_lines["time"], y=df_uncovered_lines["new_uncovered_lines"],
                   name="new uncovered lines",
                   mode="lines",
                   line=dict(width=0.5, color="rgb(200, 10, 10)"), stackgroup="one", legendgroup="group2"), row=2, col=1)
    # graph 4
    fig_subplots.add_trace(go.Scatter(x=df_uncovered_lines["time"], y=df_uncovered_lines["new_uncovered_lines_percent"], fill='tozeroy', mode='none'), row=2, col=2)
    # graph 5
    fig_num_of_tests = make_subplots(specs=[[{"secondary_y": True}]])
    fig_num_of_tests.add_trace(
        go.Scatter(x=df_test_data["time"], y=df_test_data["tests_run"], name="Number of Tests Run",
                   line=dict(width=2, color="rgb(0, 0, 0)")), secondary_y=False)
    fig_num_of_tests.add_trace(go.Scatter(x=df_test_data["time"], y=df_test_data["failures"], name="Number of Failures",
                                          line=dict(width=2, color="rgb(200, 0, 0)")), secondary_y=True)
    fig_num_of_tests.update_layout(title="Number of Tests and Failures")
    fig_num_of_tests.update_yaxes(title="Number of Tests", secondary_y=False)
    fig_num_of_tests.update_yaxes(title="Number of Failures", secondary_y=True)
    # graph 6

    fig_table = go.Figure(data=[go.Table(
        header=dict(values=list(df_heatmap.columns),
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[df_heatmap[column] for column in list(df_heatmap.columns)],
                   fill_color='lavender',
                   align='left'))
    ])
    fig_line_scatterplot = px.scatter(df_heatmap, x="file_name_short", y="line_number", color="coverage",
                                      size=df_heatmap["count"].to_list())
    fig_line_heatmap = px.imshow(heatmap_uncovered)
    #fig_line_heatmap = px.scatter(df_heatmap, x="file_name_short", y="line_number", color="coverage", size=df_heatmap["count"].to_list())

    return html.Div([
        dcc.Graph(figure=fig_subplots),
        dcc.Graph(figure=fig_num_of_tests),
        dcc.Graph(figure=fig_line_scatterplot),
        dcc.Graph(figure=fig_line_heatmap),
        dcc.Graph(figure=fig_table)
    ])


if __name__ == "__main__":
    # jacoco repo requires java 17 or newer
    # git_url = "https://github.com/apache/logging-log4j2"  # requires java 1.5 for old builds.  Jacoco.exec doesn't get generated
    # breaks when editing xml, old versions fail because they require java 1.5 and current maven doesn't support that
    # commits since 2019 work but barely any change
    # git_url = "https://github.com/junit-team/junit4"  # working well for builds 2019 or newer
    # git_url = "https://github.com/google/guava"       # no report, maven execution fails
    # git_url = "https://github.com/apache/maven"       # needs xml cleanup and report-aggregator, setting exec path might help
    # git_url = "https://github.com/apache/commons-math" # weird pom.xml structure
    # git_url = "https://github.com/vaadin/flow"        # no license key
    # git_url = "https://github.com/LeonardFiedrowicz/MavenJacocoExample"  # perfect

    # analyze_file_activity(url=git_url, num_commits=15, start_date="2019-01-01")
    create_dash_app()
    # get_coverage(git_url=git_url, path="D:\\Coverage", module_path=None, coverage_tool="jacoco", num_commits=15, start_date="2019-01-01")
