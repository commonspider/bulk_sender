from dash import callback, Output, Input, State, set_props
from dash.dcc import Store
from dash_mantine_components import Code
from selenium.webdriver.remote.webdriver import WebDriver
from wautils import start_driver

# Driver
driver: list[WebDriver | None] = [None]


def driver_init(**kwargs):
    driver[0] = start_driver(**kwargs)


def get_driver() -> WebDriver:
    return driver[0]


# Logger
logger = Code(children="Logs:", id="code_logger", block=True)
appender = Store(id="store_appender")


@callback(
    Output("code_logger", "children"),
    Output("store_appender", "data"),
    Input("store_appender", "data"),
    State("code_logger", "children"),
    prevent_initial_call=True
)
def append_log(new_line: str, log_history: str):
    return (
        f"{log_history}\n> {new_line}",
        None
    )


def log(message: str):
    set_props("store_appender", {"data": message})
