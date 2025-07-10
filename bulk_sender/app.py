import uuid
from typing import Any

from dash import Dash
from dash.dcc import Store
from dash_mantine_components import MantineProvider, Table, Accordion, AccordionItem, Stack, AccordionControl, \
    AccordionPanel, SimpleGrid, Title

from .common import logger, appender, log
from .steps import steps


def create_app():
    app = Dash(on_error=error_handler)
    app.layout = MantineProvider(
        #forceColorScheme="dark",
        children=SimpleGrid(
            cols=2,
            children=[
                Stack([
                    create_accordion(dict([step() for step in steps])),
                    logger,
                    appender,
                ]),
                Stack(
                    children=[
                        Title("Contatti selezionati"),
                        Table(data={"caption": "Nessun contatto selezionato"}, id="table_selected"),
                        Title("Tutti i contatti"),
                        Table(data={"caption": "Nessun contatto"}, id="table_contacts"),
                    ]
                ),
            ]
        )
    )
    return app


def error_handler(err):
    log(f"Exception: {err}")


def create_accordion(items: dict[str, Any]):
    return Accordion([
        AccordionItem([
            AccordionControl(f"{i + 1}. {title}"),
            AccordionPanel(SimpleGrid(content, cols=2)),
        ], value=str(i))
        for i, (title, content) in enumerate(items.items())
    ])
