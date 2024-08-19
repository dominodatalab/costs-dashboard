import os

import dash_bootstrap_components as dbc
from dash import Dash
from dash import dcc
from dash import html
from dash.dependencies import Input
from dash.dependencies import Output

from domino_cost.constants import window_to_param
from domino_cost.cost import get_cost_cards
from domino_cost.cost import get_cumulative_cost_graph
from domino_cost.cost import get_distributed_execution_cost
from domino_cost.cost import get_domino_namespace
from domino_cost.cost import get_dropdown_filters
from domino_cost.cost import get_execution_cost_table
from domino_cost.cost import get_histogram_charts
from domino_cost.cost import workload_cost_details
from domino_cost.cost_enums import CostLabels
from domino_cost.requests_helpers import get_aggregated_allocations
from domino_cost.requests_helpers import get_cloud_cost_sum
from domino_cost.requests_helpers import get_token

api_host = os.environ["DOMINO_API_HOST"]
api_proxy = os.environ["DOMINO_API_PROXY"]

namespace = get_domino_namespace(api_host)
cost_url = f"http://domino-cost.{namespace}:9000"
auth_url = f"{api_proxy}/account/auth/service/authenticate"

auth_header = {"X-Authorization": get_token(auth_url)}

requests_pathname_prefix = "/{}/{}/r/notebookSession/{}/".format(
    os.environ.get("DOMINO_PROJECT_OWNER"),
    os.environ.get("DOMINO_PROJECT_NAME"),
    os.environ.get("DOMINO_RUN_ID"),
)
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    routes_pathname_prefix=None,
    requests_pathname_prefix=requests_pathname_prefix,
)

app.layout = html.Div(
    [
        html.H2(
            "Domino Cost Management Report",
            style={"textAlign": "center", "margin-top": "30px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.H4("Data select", style={"margin-top": "20px"}),
                    width=2,
                ),
                dbc.Col(html.Hr(style={"margin-top": "40px"}), width=10),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.P(
                        "Time Span:",
                        style={"float": "right", "margin-top": "5px"},
                    ),
                    width=1,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="time_span_select",
                        options=window_to_param,
                        value="30d",
                        clearable=False,
                        searchable=False,
                    ),
                    width=2,
                ),
                dbc.Col(width=9),
            ],
            style={"margin-top": "30px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.H4("Filter data by", style={"margin-top": "20px"}),
                    width=2,
                ),
                dbc.Col(html.Hr(style={"margin-top": "40px"}), width=10),
            ],
            style={"margin-top": "50px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.P(
                        "Billing Tag:",
                        style={"float": "right", "margin-top": "5px"},
                    ),
                    width=1,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="billing_select",
                        options=["No data"],
                        clearable=True,
                        searchable=True,
                        style={"width": "100%", "whiteSpace": "nowrap"},
                    ),
                    width=3,
                ),
                dbc.Col(
                    html.P(
                        "Project:",
                        style={"float": "right", "margin-top": "5px"},
                    ),
                    width=1,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="project_select",
                        options=["No data"],
                        clearable=True,
                        searchable=True,
                        style={"width": "100%", "whiteSpace": "nowrap"},
                    ),
                    width=3,
                ),
                dbc.Col(
                    html.P("User:", style={"float": "right", "margin-top": "5px"}),
                    width=1,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="user_select",
                        options=["No data"],
                        clearable=True,
                        searchable=True,
                        style={"width": "100%", "whiteSpace": "nowrap"},
                    ),
                    width=3,
                ),
            ],
            style={"margin-top": "30px"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.CardBody(
                                [
                                    html.H3("Total"),
                                    html.H4("Loading", id="totalcard"),
                                ]
                            )
                        ]
                    )
                ),
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.CardBody(
                                [
                                    html.H3("Cloud"),
                                    html.H4("Loading", id="cloudcard"),
                                ]
                            )
                        ]
                    )
                ),
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.CardBody(
                                [
                                    html.H3("Compute"),
                                    html.H4("Loading", id="computecard"),
                                ]
                            )
                        ]
                    )
                ),
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.CardBody(
                                [
                                    html.H3("Storage"),
                                    html.H4("Loading", id="storagecard"),
                                ]
                            )
                        ]
                    )
                ),
            ],
            style={"margin-top": "50px"},
        ),
        dcc.Loading(
            children=[
                dcc.Graph(
                    id="cumulative-daily-costs",
                    config={"displayModeBar": False},
                    style={"margin-top": "40px"},
                )
            ],
            type="default",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="user_chart", config={"displayModeBar": False})),
                dbc.Col(dcc.Graph(id="project_chart", config={"displayModeBar": False})),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="org_chart", config={"displayModeBar": False})),
                dbc.Col(dcc.Graph(id="tag_chart", config={"displayModeBar": False})),
            ]
        ),
        html.H4("Workload Cost Details", style={"margin-top": "50px"}),
        html.Div(id="table-container"),
        dbc.Row([], style={"margin-top": "50px"}),
    ],
    className="container",
)


@app.callback(
    [
        Output("billing_select", "options"),
        Output("project_select", "options"),
        Output("user_select", "options"),
        Output("totalcard", "children"),
        Output("cloudcard", "children"),
        Output("computecard", "children"),
        Output("storagecard", "children"),
        Output("cumulative-daily-costs", "figure"),
        Output("user_chart", "figure"),
        Output("project_chart", "figure"),
        Output("org_chart", "figure"),
        Output("tag_chart", "figure"),
        Output("table-container", "children"),
    ],
    [
        Input("time_span_select", "value"),
        Input("billing_select", "value"),
        Input("project_select", "value"),
        Input("user_select", "value"),
    ],
)
def update(time_span, billing_tag, project, user):
    cloud_cost_sum = get_cloud_cost_sum(time_span, base_url=cost_url, headers=auth_header)
    allocations = get_aggregated_allocations(time_span, base_url=cost_url, headers=auth_header)
    if not allocations:
        return (
            [],
            [],
            [],
            "No data",
            "No data",
            "No data",
            {},
            None,
            None,
            None,
            None,
            None,
        )

    cost_table = get_execution_cost_table(allocations)
    distributed_cost_table = get_distributed_execution_cost(cost_table, cloud_cost_sum)

    if user is not None:
        distributed_cost_table = distributed_cost_table[distributed_cost_table[CostLabels.USER] == user]

    if project is not None:
        distributed_cost_table = distributed_cost_table[distributed_cost_table[CostLabels.PROJECT_NAME] == project]

    if billing_tag is not None:
        distributed_cost_table = distributed_cost_table[distributed_cost_table[CostLabels.BILLING_TAG] == billing_tag]

    return (
        *get_dropdown_filters(distributed_cost_table),
        *get_cost_cards(distributed_cost_table),
        get_cumulative_cost_graph(distributed_cost_table, time_span),
        *get_histogram_charts(distributed_cost_table),
        workload_cost_details(distributed_cost_table),
    )


@app.callback([Output("user_select", "value")], [Input("user_chart", "clickData")])
def user_clicked(clickData):
    if clickData is not None:
        x_value = clickData["points"][0]["y"]
        return [x_value]
    else:
        return [None]


@app.callback([Output("project_select", "value")], [Input("project_chart", "clickData")])
def project_clicked(clickData):
    if clickData is not None:
        x_value = clickData["points"][0]["y"]
        return [x_value]
    else:
        return [None]


@app.callback([Output("billing_select", "value")], [Input("tag_chart", "clickData")])
def billing_tag_clicked(clickData):
    if clickData is not None:
        x_value = clickData["points"][0]["y"]
        return [x_value]
    else:
        return [None]


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8888)  # Domino hosts all apps at 0.0.0.0:8888
