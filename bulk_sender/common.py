import json
from pathlib import Path

from dash import callback, Output, Input, State, set_props
from dash.dcc import Store
from dash_mantine_components import Code

# Config
config = {
    "whatsapp_url": "https://web.whatsapp.com/",
    "button_file": "File",
    "button_download": "Scarica",
    "button_extension": "Valori separati da virgola",
    "col_name": "Nome",
    "col_surname": "Cognome",
    "col_phone": "Numero di Telefono",
}


def load_config(path: str):
    if Path(path).exists():
        with open(path) as f:
            config.update(json.load(f))
    config["config_path"] = path
    return config


def update_config(**values):
    config.update(values)


def save_config():
    copy = config.copy()
    path = copy.pop("config_path")
    data = json.dumps(copy, indent=4)
    with open(path, "w") as f:
        f.write(data)


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
