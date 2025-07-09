import base64
from io import StringIO
from typing import Callable, Sequence, Text

import pandas
from dash import callback, Output, Input, State
from dash.dcc import Store, Upload
from dash.exceptions import PreventUpdate
from dash_mantine_components import Button, TextInput, Textarea, Code, Card
from pandas import DataFrame

from .common import config, update_config
from .common import log
from .driver import open_tab, download_contacts, send_wa_message, focus_tab

steps: list[Callable[[], tuple[str, list]]] = []


def step(f):
    steps.append(f)
    return f


# Download Contacts
@step
def step_download_contacts():
    return (
        "Scarica il foglio dei contatti",
        [
            TextInput(config.get("contacts_url", ""), id="input_contacts_url"),
            "Indirizzo del foglio di Google con i contatti",
            TextInput(config.get("button_file", ""), id="input_button_file"),
            "Testo del pulsante 'File' di Google Sheets",
            TextInput(config.get("button_download", ""), id="input_button_download"),
            "Testo del pulsante 'Download' di Google Sheets",
            TextInput(config.get("button_extension", ""), id="input_button_extension"),
            "Testo del pulsante di Google Sheets per scaricare con estensione csv",
            Button("Download", id="button_download_contacts"),
            "Apre una nuova tab, automaticamente scarica il file ed infine chiude la tab.",
        ]
    )


@callback(
    Output("button_download_contacts", "n_clicks", allow_duplicate=True),
    Input("button_download_contacts", "n_clicks"),
    State("input_contacts_url", "value"),
    State("input_button_file", "value"),
    State("input_button_download", "value"),
    State("input_button_extension", "value"),
    prevent_initial_call=True
)
def callback_update_contacts(_, url: str, file: str, download: str, extension: str):
    update_config(contacts_url=url, button_file=file, button_download=download, button_extension=extension)
    download_contacts(url, file, download, extension)
    log("Contatti scaricati")
    return _


# Whatsapp Login
@step
def whatsapp_login():
    return (
        "Whatsapp Login",
        [
            TextInput(config.get("whatsapp_url", ""), id="input_wa_url"),
            "Indirizzo di Whatsapp web.",
            Button("Login", id="button_open_wa"),
            "Clicca il pulsante, effettua il login e chiudi eventuali popups. "
            "Lascia la tab aperta e continua qua.",
            Store(id="store_wa_tab_id")
        ]
    )


@callback(
    Output("store_wa_tab_id", "data"),
    Input("button_open_wa", "n_clicks"),
    State("input_wa_url", "value"),
    prevent_initial_call=True
)
def open_wa(_, url: str):
    update_config(whatsapp_url=url)
    uid = open_tab(url)
    log(f"Tab di Whatsapp aperta")
    return uid


# Load Contacts
@step
def load_contacts():
    return (
        "Carica i contatti dal file",
        [
            Upload(
                id="upload_contacts",
                children=Card([
                    Text("Drag and Drop oppure"),
                    Button("Seleziona il file")
                ]),
            ),
        ]
    )


@callback(
    Output("table_contacts", "data", allow_duplicate=True),
    Input("upload_contacts", "contents"),
    prevent_initial_call=True,
)
def show_contacts(content: str):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string).decode()
    df = pandas.read_csv(StringIO(decoded), sep=",")
    head, rows = get_contacts_table(df)
    log("Contatti caricati")
    return {"head": head, "body": rows}


# Select contacts
@step
def select_contacts():
    return (
        "Seleziona i contatti",
        [
            TextInput(id="input_contacts_selection"),
            "Scrivi il numero delle righe dei contatti che vuoi selezionare. "
            "Dev'essere una sequenza di numeri o coppie di numeri separati da una virgola. "
            "(Esempio: 1,4-7,9 seleziona i contatti 1, 4, 5, 6, 7, 9)",
            TextInput(config.get("col_name", ""), id="input_col_name"),
            "Nome della colonna con i nomi.",
            TextInput(config.get("col_surname", ""), id="input_col_surname"),
            "Nome della colonna con i cognomi.",
            TextInput(config.get("col_phone", ""), id="input_col_phone"),
            "Nome della colonna con i numeri di telefono.",
            Button("Seleziona", id="button_contacts_select"),
        ]
    )


@callback(
    Output("table_selected", "data", allow_duplicate=True),
    Input("button_contacts_select", "n_clicks"),
    State("input_contacts_selection", "value"),
    State("input_col_name", "value"),
    State("input_col_surname", "value"),
    State("input_col_phone", "value"),
    State("table_contacts", "data"),
    prevent_initial_call=True
)
def callback_select_contacts(_, selection: str, name_col: str, surname_col: str, phone_col: str, contacts: dict):
    rows = []
    for item in selection.split(","):
        parts = item.split("-")
        if len(parts) == 1:
            rows.append(int(parts[0]))
        elif len(parts) == 2:
            rows.extend(range(int(parts[0]), int(parts[1]) + 1))
        else:
            log("Selezione invalida")
            raise PreventUpdate
    try:
        name_i = contacts["head"].index(name_col)
        surname_i = contacts["head"].index(surname_col)
        phone_i = contacts["head"].index(phone_col)
    except ValueError:
        log("Colonna non trovata")
        raise PreventUpdate
    body = []
    for row in contacts["body"]:
        if int(row[0]) not in rows:
            continue
        name = capitalize(row[name_i])
        surname = capitalize(row[surname_i])
        phone = parse_numer(row[phone_i])
        body.append((row[0], name, surname, phone))
    log("Contatti selezionati")
    return {"head": ["NUM", name_col, surname_col, phone_col], "body": body}


# Send Messages
@step
def send_messages():
    return (
        "Invia i messaggi",
        [
            Textarea(id="textarea_skeleton"),
            "Scrivi il tuo message. Puoi il usare il nome delle colonne tra parentesi graffe come placeholder. "
            "(Esempio: Ciao {Nome}! Come stai?)",
            Button("INVIA!", id="button_send_messages"),
            "Invia tutto e ciaone!",
        ]
    )


@callback(
    Output("button_send_messages", "n_clicks", allow_duplicate=True),
    Input("button_send_messages", "n_clicks"),
    State("textarea_skeleton", "value"),
    State("input_col_phone", "value"),
    State("table_selected", "data"),
    State("store_wa_tab_id", "data"),
    prevent_initial_call=True
)
def callback_send_messages(_, skeleton: str, col_phone: str, selected: dict, tab: str):
    update_config(col_phone=col_phone)
    focus_tab(tab)
    cols: list = selected["head"]
    phone_index = cols.index(col_phone)
    for row in selected["body"]:
        phone = row[phone_index]
        if phone is not None:
            text = skeleton.format(**dict(zip(cols, row)))
            if send_wa_message(phone, text):
                log(f"Messaggio inviato a {phone}")
            else:
                log(f"ATTENZIONE! {phone} non ha whatsapp!")
    log("Finito!")
    return _


# Utils
def get_contacts_table(df: DataFrame) -> tuple[Sequence, Sequence]:
    return (
        ("NUM", *df.columns),
        [
            (str(int(i) + 2), *row)
            for i, row in df.iterrows()
        ]
    )


def capitalize(string: str):
    if isinstance(string, str):
        return " ".join([part.capitalize() for part in string.split()])
    else:
        return ""


def parse_numer(obj):
    if isinstance(obj, (str, int)):
        return str(obj)
    else:
        return ""
