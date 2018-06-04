from bokeh.layouts import column, widgetbox, gridplot, layout, Spacer
from bokeh.models import ColumnDataSource, Div, Row
from bokeh.models.widgets import Button, DataTable, TableColumn, RadioGroup, CheckboxGroup, MultiSelect
from bokeh.models.widgets.inputs import TextInput
from bokeh.models.widgets.tables import BooleanFormatter, CheckboxEditor
from bokeh.core.enums import Enumeration, enumeration
from bokeh.core.properties import Enum
from bokeh.io import curdoc
# from nlp_architect.utils.text_preprocess import simple_normalizer
import numpy as np
import pandas
import socket
import pickle
import csv
import sys
import os
import time


out_path = "export.csv"
hash2group = {}
all_phrases = []
max_visible_phrases = 5000
seed_after_search = ''
working_text = 'working...'


def get_phrases(top_n=100000):
    global all_phrases
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to server and send data
        sock.connect(("localhost", 1111))
        print('sending a get_vocab request')
        sock.sendall(bytes('get_vocab' + "\n", "utf-8"))
        # Receive data from the server and shut down
        data = b""
        while True:
            packet = sock.recv(4096)
            if not packet:
                break
            data += packet
        received = pickle.loads(data)
        all_phrases.extend(received)
        print('vocab len = ' + str(len(all_phrases)))
        # print("Received: {}".format(received))

    finally:
        sock.close()


def clean_group(phrase_group):
    text = [x.lstrip() for x in phrase_group.split(';')]
    return min(text, key=len)


# initialize
get_phrases()
expand_columns = [
    TableColumn(field="res", title="Results"),
    TableColumn(field="score", title="Score")
]

# create ui components
seed_input_title = 'Please enter a comma separated seed list of terms:'
seed_input_box = TextInput(title=seed_input_title, value="USA, Israel, France", width=450)
search_input_box = TextInput(title="Search:", value="", width=300)
expand_button = Button(label="Expand", button_type="success", width=150)
clear_seed_button = Button(label="Clear", button_type="success", css_classes=['clear_button'], width=50)
export_button = Button(label="Export", button_type="success", css_classes=['export_button'], width=100)
expand_table_source = ColumnDataSource(data=dict())
expand_table = DataTable(source=expand_table_source, columns=expand_columns, width=500, css_classes=['expand_table'])
phrases_list = MultiSelect(title="", value=[],options=all_phrases[0:max_visible_phrases], width=300, size=27)
checkbox_group = CheckboxGroup(labels=["Show extracted phrases"], active=[], width=400)
search_box_area = column(children=[Div(width=480)])
phrases_area = column(children=[Div(width=300)])
seed_layout = Row(seed_input_box,column(Div(height=0, width=0),clear_seed_button))
working_label = Div(text="", style={'color':'red'})
table_layout = Row(expand_table,Div(width=25), column(Div(height=350),export_button,working_label))
grid = layout([
                [Div(width=500),Div(text="<H1>Set Expansion Demo</H1>")],
                [checkbox_group,seed_layout],
                [search_box_area,Div(width=100),expand_button],
                [phrases_area,Div(width=100),table_layout]
            ])


# define callbacks
def conv(val):
    if val == np.nan:
        return 0 # or whatever else you want to represent your NaN with
    return val


def row_selected_callback(attr, old, new):
    selected_rows = new.indices
    values = ''
    for x in selected_rows:
        values += (expand_table_source.data['res'][x] + ', ')
    values = values[:-2]
    seed_input_box.value = values


def show_phrases_callback(checked_value):
    global search_box_area, phrases_area
    if len(checked_value) == 1:
        search_box_area.children=[search_input_box]
        phrases_area.children=[phrases_list]
    else:
        search_box_area.children=[]
        phrases_area.children=[]


def get_expand_results_callback():
    seed = seed_input_box.value
    # print('seed= ' + user_input)
    if seed == '':
        expand_table_source.data = {
            'res': [''],
            'score': ['']
        }
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to server and send data
            sock.connect(("localhost", 1111))
            sock.sendall(bytes(seed + "\n", "utf-8"))
            # Receive data from the server and shut down
            # length = sock.recv()
            received = pickle.loads(sock.recv(2000000))
            print("Sent:     {}".format(seed))
            # print("Received: {}".format(received))
            res = [x[0] for x in received]
            scores = [y[1] for y in received]
            expand_table_source.data = {
                'res': res,
                'score': scores
            }
        finally:
            sock.close()


def search_callback(value, old, new):
    global all_phrases, phrases_list, seed_after_search
    # new_phrases = [x for x in all_phrases if x.startswith(new)]
    new_phrases = [x for x in all_phrases if (new.lower() in x.lower() or x.lower()==new.lower())]
    phrases_list.options=new_phrases[0:max_visible_phrases]
    seed_after_search = seed_input_box.value


def phrase_selected_callback(attr, old, selected_phrases):
    values = '' if len(search_input_box.value) == 0 else seed_after_search + ', '
    for x in selected_phrases:
        values += x + ', '
    values = values[:-2]
    seed_input_box.value = values


def clear_seed_callback():
    seed_input_box.value = ''


def export_data_callback():
    if working_label.text != working_text:
        print('saving expansion results to: ' + out_path)
        working_label.style = {'color': 'red'}
        working_label.text=working_text
        table_df = pandas.DataFrame(expand_table_source.data)
        table_df.to_csv(out_path)
        working_label.style={'color':'green'}
        working_label.text = 'Done!'
        time.sleep(1)
        working_label.text = ''


# set callbacks
expand_button.on_click(get_expand_results_callback)
expand_table_source.on_change('selected', row_selected_callback)
checkbox_group.on_click(show_phrases_callback)
search_input_box.on_change('value',search_callback)
phrases_list.on_change('value', phrase_selected_callback)
clear_seed_button.on_click(clear_seed_callback)
export_button.on_click(export_data_callback)


# arrange components in page
doc = curdoc()
main_title = "Set Expansion Demo"
doc.title = main_title
doc.add_root(grid)


# present initial example:
get_expand_results_callback()