import base64
import time
from io import StringIO, BytesIO
from typing import Callable, Sequence, Text

import PIL.Image
import pandas
from dash import callback, Output, Input, State, set_props
from dash.dcc import Upload
from dash_mantine_components import Button, TextInput, Textarea, Card, Image
from pandas import DataFrame
from wautils import login_qr, post_login, login_code, send_message

from .common import log, get_driver

steps: list[Callable[[], tuple[str, list]]] = []


def step(f):
    steps.append(f)
    return f


# Whatsapp Login
@step
def step_login():
    return (
        "Whatsapp Login",
        [
            Button("Login con QR", id="button_login_qr"),
            "Clicca qui per mostrare il qr",
            Image(id="image_qr"), "da scannerizzare con l'app",
            Button("Login con codice", id="button_login_code"),
            "Clicca qui per mostrate il codice da inserire nell'app. Prima compila i campi sotto",
            TextInput(id="input_code", disabled=True), "Codice",
            TextInput("Italia", id="input_country", persistence=True, persistence_type="local"), "Stato di appartenenza (usato per il prefisso)",
            TextInput(id="input_phone", persistence=True, persistence_type="local"), "Numero di telefono",
        ]
    )


@callback(
    Output("button_login_qr", "n_clicks"),
    Input("button_login_qr", "n_clicks"),
    prevent_initial_call=True,
    running=[
        (Output("button_login_qr", "disabled"), True, False),
        (Output("button_login_code", "disabled"), True, False),
    ],
)
def callback_login_qr(_):
    driver = get_driver()
    data = login_qr(driver)
    set_props("image_qr", {"src": PIL.Image.open(BytesIO(data))})
    post_login(driver)
    log("Login effettuato")
    return _


@callback(
    Output("button_login_code", "n_clicks"),
    Input("button_login_code", "n_clicks"),
    State("input_country", "value"),
    State("input_phone", "value"),
    prevent_initial_call=True,
    running=[
        (Output("button_login_qr", "disabled"), True, False),
        (Output("button_login_code", "disabled"), True, False),
    ],
)
def callback_login_code(_, country: str, phone: str):
    driver = get_driver()
    code = login_code(driver, country, phone)
    set_props("input_code", {"value": code})
    post_login(driver)
    log("Login effettuato")
    return _


# Load Contacts
@step
def step_load_contacts():
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
            "Estensioni supportate: csv"
        ]
    )


@callback(
    Output("table_contacts", "data", allow_duplicate=True),
    Input("upload_contacts", "contents"),
    prevent_initial_call=True,
)
def callback_load_contacts(content: str):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string).decode()
    df = pandas.read_csv(StringIO(decoded), sep=",")
    head, rows = get_contacts_table(df)
    log("Contatti caricati")
    return {"head": head, "body": rows}


# Select contacts
@step
def step_select_contacts():
    return (
        "Seleziona i contatti",
        [
            TextInput(id="input_contacts_selection"),
            "Scrivi il numero delle righe dei contatti che vuoi selezionare. "
            "Dev'essere una sequenza di numeri o coppie di numeri separati da una virgola. "
            "(Esempio: 1,4-7,9 seleziona i contatti 1, 4, 5, 6, 7, 9)",
            TextInput(id="input_col_name", persistence=True, persistence_type="local"),
            "Nome della colonna con i nomi.",
            TextInput(id="input_col_phone", persistence=True, persistence_type="local"),
            "Nome della colonna con i numeri di telefono.",
            Button("Seleziona", id="button_contacts_select"),
        ]
    )


@callback(
    Output("table_selected", "data", allow_duplicate=True),
    Input("button_contacts_select", "n_clicks"),
    State("input_contacts_selection", "value"),
    State("input_col_name", "value"),
    State("input_col_phone", "value"),
    State("table_contacts", "data"),
    prevent_initial_call=True
)
def callback_select_contacts(_, selection: str, name_col: str, phone_col: str, contacts: dict):
    rows = []
    for item in selection.split(","):
        parts = item.split("-")
        if len(parts) == 1:
            rows.append(int(parts[0]))
        elif len(parts) == 2:
            rows.extend(range(int(parts[0]), int(parts[1]) + 1))
        else:
            log("Selezione invalida")
            return {"caption": "Selectione invalida"}
    try:
        name_i = contacts["head"].index(name_col)
        phone_i = contacts["head"].index(phone_col)
    except ValueError:
        log("Colonna non trovata")
        return {"caption": "Colonna non trovata"}
    body = []
    for row in contacts["body"]:
        if int(row[0]) not in rows:
            continue
        name = capitalize(row[name_i])
        phone = parse_number(row[phone_i])
        body.append((row[0], name, phone))
    log("Contatti selezionati")
    return {"head": ["NUM", name_col, phone_col], "body": body}


# Send Messages
@step
def step_send_messages():
    return (
        "Invia i messaggi",
        [
            Textarea(id="textarea_skeleton", persistence=True, persistence_type="local"),
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
    prevent_initial_call=True,
    running=[
        (Output("button_send_messages", "disabled"), True, False),
    ],
)
def callback_send_messages(_, skeleton: str, col_phone: str, selected: dict):
    driver = get_driver()
    cols: list = selected["head"]
    phone_index = cols.index(col_phone)
    for row in selected["body"]:
        phone = row[phone_index]
        if phone is not None:
            text = skeleton.format(**dict(zip(cols, row)))
            if send_message(driver, phone, text):
                log(f"Messaggio inviato a {phone}")
                time.sleep(0.5)
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
        return None


def parse_number(obj):
    if isinstance(obj, (str, int)):
        return str(obj)
    else:
        return None
