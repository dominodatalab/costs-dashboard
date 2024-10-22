import logging
import os
from datetime import date
from datetime import timedelta

import dash_bootstrap_components as dbc
from dash import Dash
from dash import dcc
from dash import html
from dash.dependencies import Input
from dash.dependencies import Output

from domino_cost import config
from domino_cost.constants import window_to_param
from domino_cost.cost import Cost
from domino_cost.cost import get_cost_cards
from domino_cost.cost import get_cumulative_cost_graph
from domino_cost.cost import get_distributed_execution_cost
from domino_cost.cost import get_dropdown_filters
from domino_cost.cost import get_execution_cost_table
from domino_cost.cost import get_histogram_charts
from domino_cost.cost import get_last_n_days
from domino_cost.cost import workload_cost_details
from domino_cost.cost_enums import CostLabels
from domino_cost.requests_helpers import get_aggregated_allocations
from domino_cost.requests_helpers import get_cloud_cost_sum
from domino_cost.requests_helpers import get_token

logger = logging.getLogger(__name__)

api_host = os.environ["DOMINO_API_HOST"]
api_proxy = os.environ["DOMINO_API_PROXY"]

cost = Cost(api_host, api_proxy)

auth_header = {"X-Authorization": get_token(cost.auth_url)}

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

today = date.today()
last_30 = get_last_n_days(29)

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
                        value="29d",
                        clearable=False,
                        searchable=False,
                    ),
                    width=2,
                    style={"height": "50px", "margin-top": "5px", "display": "inline-block"},
                ),
                dbc.Col(
                    dcc.DatePickerRange(
                        id="date-picker-range",
                        min_date_allowed=date(2023, 1, 1),
                        max_date_allowed=today,
                        initial_visible_month=today,
                        end_date=today,
                    ),
                    width=3,
                    style={"height": "50px", "margin-top": "5px"},
                ),
                dbc.Col(dcc.Input(id="date_time_select", style={"display": "none"}), width=6),
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
                    style={"display": "block"},
                    id="billing-tag-select-dropdown-p",
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
                    id="billing-tag-select-dropdown-col",
                    style={"display": "block"},
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
                dbc.Col(
                    dbc.Card(
                        children=[
                            dbc.CardBody(
                                [
                                    html.H3("Cloud Services"),
                                    html.H4("Loading", id="cloudcard"),
                                ]
                            )
                        ]
                    ),
                    id="cloud-cost-card",
                    style={"display": "block"},
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
        html.Div(id="workload-cost-table-container"),
        dbc.Row([], style={"margin-top": "50px"}),
    ],
    className="container",
)


@app.callback(
    Output("time_span_select", "value"), Input("date-picker-range", "start_date"), Input("date-picker-range", "end_date")
)
def update_output(start_date, end_date):
    if start_date and end_date:
        return cost.format_date(start_date) + "," + cost.format_date(end_date)
    else:
        return "29d"


def update_configs(time_span):
    cloud_cost_sum = get_cloud_cost_sum(time_span, base_url=cost.cost_url, headers=auth_header)
    if cloud_cost_sum > 0:
        config.cloud_cost_available = True
    else:
        config.cloud_cost_available = False
    config.default_is_updated = True


@app.callback(Output(component_id="cloud-cost-card", component_property="style"), [Input("time_span_select", "value")])
def show_hide_cloud_cost(time_span):
    if not config.default_is_updated:
        update_configs(time_span)
    if config.cloud_cost_available:
        return {"display": "block"}
    else:
        return {"display": "none"}


@app.callback(
    Output("date_time_select", "value"),
    Input("time_span_select", "value"),
)
def update_output_date(time_span_select):
    suffix = "," + cost.format_date(str(today))
    if str(time_span_select).endswith("d"):
        logger.info("processing data for span time %s", time_span_select)
        start_date = today - timedelta(days=int(time_span_select.split("d")[0]))
        return cost.format_date(str(start_date)) + suffix
    elif time_span_select:
        logger.info("processing data for span time %s", time_span_select)
        return time_span_select
    else:
        return cost.format_date(str(last_30)) + suffix


output_list = [
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
    Output("workload-cost-table-container", "children"),
]


@app.callback(
    *output_list,
    [
        Input("date_time_select", "value"),
        Input("billing_select", "value"),
        Input("project_select", "value"),
        Input("user_select", "value"),
    ],
)
def update(time_span, billing_tag, project, user):
    cloud_cost_sum = get_cloud_cost_sum(time_span, base_url=cost.cost_url, headers=auth_header)
    allocations = get_aggregated_allocations(time_span, base_url=cost.cost_url, headers=auth_header)

    if not allocations:
        logger.info("No allocations found for the given time span")
        return (
            [],
            [],
            [],
            "No data",
            "No data",
            "No data",
            {},
            {},
            {},
            {},
            {},
            {},
            None,
        )

    cost_table = get_execution_cost_table(allocations)
    distributed_cost_table = get_distributed_execution_cost(cost_table, cloud_cost_sum)

    if user is not None:
        distributed_cost_table = distributed_cost_table[distributed_cost_table[CostLabels.USER.value] == user]

    if project is not None:
        distributed_cost_table = distributed_cost_table[distributed_cost_table[CostLabels.PROJECT_NAME.value] == project]

    if billing_tag is not None:
        distributed_cost_table = distributed_cost_table[
            distributed_cost_table[CostLabels.BILLING_TAG.value] == billing_tag
        ]

    return (
        *get_dropdown_filters(distributed_cost_table),
        *get_cost_cards(distributed_cost_table),
        get_cumulative_cost_graph(distributed_cost_table, time_span),
        *get_histogram_charts(distributed_cost_table),
        workload_cost_details(distributed_cost_table),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Started Cost Dashboard App")
    app.run_server(host="0.0.0.0", port=8888)  # Domino hosts all apps at 0.0.0.0:8888
