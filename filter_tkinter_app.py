import tkinter as tk
from tkinter import ttk
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
    
def choose_stations_last_line(stations, edges):
    # Ensure the 'Last line' column exists in df_stations_1
    stations['Last line'] = np.nan
    
    # Create temporary DataFrames that pair stations with their corresponding line
    temp_df_from = edges[['Station from (A)', 'Line']].drop_duplicates(subset='Station from (A)', keep='last')
    temp_df_to = edges[['Station to (B)', 'Line']].drop_duplicates(subset='Station to (B)', keep='last')
    
    # Rename columns to avoid confusion during merging
    temp_df_from.rename(columns={'Station from (A)': 'Station', 'Line': 'Line_from'}, inplace=True)
    temp_df_to.rename(columns={'Station to (B)': 'Station', 'Line': 'Line_to'}, inplace=True)
    
    # Merge the temporary DataFrames with df_stations_1
    stations = stations.merge(temp_df_from, on='Station', how='left')
    stations = stations.merge(temp_df_to, on='Station', how='left')
    
    # Update the 'Last line' column in df_stations_1 by prioritizing 'Line_to' if it exists
    stations['Last line'] = stations['Line_to'].combine_first(stations['Line_from'])
    
    # Drop the unnecessary 'Line_from' and 'Line_to' columns
    stations = stations.drop(columns=['Line_from', 'Line_to'])
    
    # Optional: Fill NaN values in 'Last line' if needed, e.g., with 'Unknown'
    stations['Last line'] = stations['Last line'].fillna('Unknown')
    
    return stations

# Define the Tkinter app class
class NetworkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("London Transport Network Visualization")

        # Read datasets
        self.df = pd.read_csv('London_transport_network.csv').dropna()
        self.df1 = pd.read_csv('London stations.csv').dropna()

        # Initial lines to display
        self.displayed_lines = ['Central', 'Waterloo & City', 'Piccadilly', 'Jubilee']

        # Data preprocessing
        self.df_stations, self.df_lines = self.preprocess_data()

        # Filter lines and edges
        self.df_filtered, self.df_stations_filtered, self.df_lines_filtered = self.filter_datasets()
        
        # Draw initial graph
        self.MyGraph = nx.Graph()
        self.fig = plt.figure(figsize=(15, 9), dpi=100)
        self.ax = self.fig.add_subplot()
        self.draw_network(self.df_stations_filtered, self.df_filtered, self.df_lines_filtered)

        # Draw Tkinter GUI
        self.draw_UI()       
    
    def draw_UI(self):
        # Init graph canvas in Tkinter
        self.draw_graph_UI()
        self.draw_inputs()
        # Packing order is important. Widgets are processed sequentially and if there
        # is no space left, because the window is too small, they are not displayed.
        # The canvas is rather flexible in its size, so we pack it last which makes
        # sure the UI controls are displayed as long as possible.
        self.pack_graph_UI()
        
    def draw_graph_UI(self):
        self.graph_frame = ttk.Frame(self.root)
        self.graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        # Init tkinter canvas
        self.canvas = FigureCanvasTkAgg(figure=self.fig, master=self.graph_frame)
        self.canvas.draw_idle()
        self.toolbar = NavigationToolbar2Tk(canvas=self.canvas, window=self.graph_frame, pack_toolbar=False)
        self.toolbar.update()
        self.canvas.mpl_connect("key_press_event", lambda event: print(f"you pressed {event.key}"))
        self.canvas.mpl_connect("key_press_event", key_press_handler)

    def pack_graph_UI(self):
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
            
    def draw_inputs(self):
        # Create a main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        
        # Define the font for the program
        window_font = ("Helvetica", 12)  # You can adjust the font family and size as needed
        s = ttk.Style()
        s.configure('my.TButton', font=window_font)
        s.configure('B1.TButton', font=window_font, background='green')
        heading_font = ("Helvetica", 14, "bold")  # Font for the heading text
        
        # Add a heading label to give users instructions
        heading_text = "Select Railway Lines"
        self.heading_label = ttk.Label(self.main_frame, text=heading_text, font=heading_font)
        self.heading_label.pack(pady=10)
        
        # Add check buttons for railway lines multi-selection
        self.checkbutton_vars = {}
        row_frame = None        
        for index, row in self.df_lines.iterrows():
            line_name = row['Line']
            self.checkbutton_vars[line_name] = tk.IntVar()
            
            # Make sure 3 checkbuttons are displayed in the same row
            # Create a new row if it's full
            if index % 3 == 0:
                row_frame = tk.Frame(self.main_frame)
                row_frame.pack(anchor=tk.CENTER)  # Align to the center

            checkbutton = tk.Checkbutton(
                row_frame, 
                text=line_name, 
                variable=self.checkbutton_vars[line_name], 
                onvalue=1, 
                offvalue=0, 
                height=2, 
                width=12,  # Adjust the width as needed
                font=window_font,  # Set the font
                command=self.update_displayed_lines
            )
            checkbutton.pack(side=tk.LEFT) 
        
        # Add a frame to hold the buttons and center them
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(anchor=tk.CENTER, side=tk.TOP)
        
        # Add "Tick All" and "Remove All" buttons
        self.tick_all_button = ttk.Button(button_frame, text="Tick All", style='my.TButton', command=self.tick_all)
        self.tick_all_button.pack(side=tk.LEFT, fill=tk.BOTH, padx=10)
        
        self.remove_all_button = ttk.Button(button_frame, text="Remove All", style='my.TButton', command=self.remove_all)
        self.remove_all_button.pack(side=tk.LEFT, fill=tk.BOTH, padx=10)
        
        # Add a button to refresh the plot
        self.refresh_button = ttk.Button(button_frame, text="Refresh Plot", style='B1.TButton', command=self.refresh_plot)
        self.refresh_button.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10)           
                
    # Function to update the displayed lines based on check button states
    def update_displayed_lines(self):
        self.displayed_lines = [
            line for line, var in self.checkbutton_vars.items() if var.get() == 1
        ]
        
    def tick_all(self):
        for var in self.checkbutton_vars.values():
            var.set(1)
        self.update_displayed_lines()

    def remove_all(self):
        for var in self.checkbutton_vars.values():
            var.set(0)
        self.update_displayed_lines()
        
    def draw_graph(self):
        # Draw plot
        self.ax.clear()
        self.draw_network(self.df_stations_filtered, self.df_filtered, self.df_lines_filtered)
        self.canvas.draw_idle()
         
    def filter_datasets(self):
        # Filter lines and edges
        df_lines_filtered = self.df_lines[self.df_lines['Line'].isin(self.displayed_lines)]
        df_filtered = self.df[self.df['Line'].isin(self.displayed_lines)]

        # Filter stations
        filtered_stations = set(df_filtered['Station from (A)']).union(set(df_filtered['Station to (B)']))
        df_stations_filtered = self.df_stations[self.df_stations['Station'].isin(filtered_stations)]
        df_stations_filtered = choose_stations_last_line(df_stations_filtered, df_filtered)
        
        return df_filtered, df_stations_filtered, df_lines_filtered

    def clean_data(self):
        # Add your data preprocessing logic here
        self.df['Station from (A)'] = self.df['Station from (A)'].str.title()
        self.df['Station to (B)'] = self.df['Station to (B)'].str.title()

        # Capitalize station names and remove unnecessary characters
        self.df1['Station'] = self.df1['Station'].str.replace('St.', 'St')
        self.df1['Station'] = self.df1['Station'].str.replace("'", "")
        self.df1['Station'] = self.df1['Station'].str.replace(r'\s*\(.*?\)\s*', '', regex=True) # Remove (...)
        self.df['Station from (A)'] = self.df['Station from (A)'].str.replace(r'\s*\(.*?\)\s*', '', regex=True)
        self.df['Station to (B)'] = self.df['Station to (B)'].str.replace(r'\s*\(.*?\)\s*', '', regex=True)

        # Correct some station names
        self.df['Station from (A)'] = self.df['Station from (A)'].replace({
            'Harrow-On-The-Hill': 'Harrow-on-the-Hill',
            'Bromley By Bow': 'Bromley-by-Bow',
            'Heathrow 123': 'Heathrow Terminals 1 2 3',
            'Heathrow Terminal Four': 'Heathrow Terminal 4',
            'Walthamstow': 'Walthamstow Central',
            'Highbury': 'Highbury & Islington',
            'Shoreditch': 'Shoreditch High Street'
        })
        self.df['Station to (B)'] = self.df['Station to (B)'].replace({
            'Harrow-On-The-Hill': 'Harrow-on-the-Hill',
            'Bromley By Bow': 'Bromley-by-Bow',
            'Heathrow 123': 'Heathrow Terminals 1 2 3',
            'Heathrow Terminal Four': 'Heathrow Terminal 4',
            'Walthamstow': 'Walthamstow Central',
            'Highbury': 'Highbury & Islington',
            'Shoreditch': 'Shoreditch High Street'
        })
        self.df1['Station'] = self.df1['Station'].str.replace('Jamess', 'James')
        
        # Replace occurrences of "and" with "&" in 'Station'
        self.df1['Station'] = self.df1['Station'].str.replace(r'\band\b', '&', regex=True)
        
    def extract_lines(self):
        # Trim station lines the last time
        self.df['Line'] = self.df['Line'].str.strip()

        self.df_lines = pd.DataFrame(self.df['Line'].str.strip().unique(), columns=['Line']) # Trim whitespaces
        colors = {
            'Bakerloo': 'brown',
            'Central': 'red',
            'Victoria': '#6EACDA',
            'Waterloo & City': '#9CDBA6',
            'Jubilee': 'grey',
            'Northern': 'black',
            'Piccadilly': 'blue',
            'Metropolitan': 'purple',
            'H & C': 'pink',
            'Circle': 'yellow',
            'District': 'green',
            'East London': 'orange',
        }
        self.df_lines['Color'] = self.df_lines['Line'].map(colors)
        
        return self.df_lines

    def extract_stations(self):
        # Trim station names the last time
        self.df['Station from (A)'] = self.df['Station from (A)'].str.strip()
        self.df['Station to (B)'] = self.df['Station to (B)'].str.strip()
        self.df1['Station'] = self.df1['Station'].str.strip()
        
        # Extract to a new DataFrame
        df_stations = pd.DataFrame(pd.concat([self.df['Station from (A)'], self.df['Station to (B)']]).unique(), columns=['Name'])
        
        df_stations_1 = df_stations.merge(self.df1, left_on='Name', right_on='Station', how='left')
        return df_stations_1

    def preprocess_data(self):
        # Add your data preprocessing logic here
        self.clean_data()        
        self.df_stations = self.extract_stations()
        self.df_lines = self.extract_lines()
        
        return self.df_stations, self.df_lines

    def refresh_plot(self):
        # Update datasets
        self.df_filtered, self.df_stations_filtered, self.df_lines_filtered = self.filter_datasets()

        # Redraw plot
        self.draw_graph()
        
    # Function to draw the network
    def draw_network(self, stations, edges, lines, figsize=(8, 3)):
        self.MyGraph.clear()

        # Add nodes
        for index, row in stations.iterrows():
            # Default color if 'Last line' is not found in 'lines' DataFrame
            default_color = 'lightgray'
            last_line_color = lines[lines['Line'] == row['Last line']]['Color'].values
            color = last_line_color[0] if len(last_line_color) > 0 else default_color

            self.MyGraph.add_node(row['Station'], pos=(row['Longitude'], row['Latitude']), color=color, border='black')


        # Add edges
        for index, row in edges.iterrows():
            first_line = row['Line']
            line_color = lines[lines['Line'] == first_line]['Color'].values[0]
            self.MyGraph.add_edge(row['Station from (A)'], row['Station to (B)'], weight=row['Distance (Kms)'], color=line_color, width=3)

        # Extract attributes from the graph to dictionaries
        pos = nx.get_node_attributes(self.MyGraph, 'pos')
        nodecolor = nx.get_node_attributes(self.MyGraph, 'color')
        edgecolor = nx.get_edge_attributes(self.MyGraph, 'color')
        edgeweight = nx.get_edge_attributes(self.MyGraph, 'weight')

        # Place the values from the dictionaries in lists
        NodeList = list(nodecolor.values())
        EdgeList = list(edgecolor.values())

        # Uncomment to create a new figure for the graph
        # fig = plt.figure(figsize=figsize)
        # ax = plt.axes()
        # Draw the graph's nodes and edges
        nodes = nx.draw_networkx_nodes(self.MyGraph, pos=pos, node_color=NodeList)
        nodes.set_edgecolor('black')
        nx.draw_networkx_edges(self.MyGraph, pos=pos, edge_color=EdgeList)
        # Draw edge labels
        edge_labels = {edge: f'{edgeweight[edge]:.2f} km' for edge in self.MyGraph.edges}
        nx.draw_networkx_edge_labels(self.MyGraph, pos, edge_labels=edge_labels, font_size=6)

        # Display the name of the stations next to their points
        for index, row in stations.iterrows():
            name = row['Station']
            offset = (0, 0.002)  # Adjust these values to reduce overlap
            # if name == "Knightsbridge":
            #     offset = (-0.002, 0.002)
            # elif name == "Northfields":
            #     offset = (-0.002, 0.002)
            # elif name == "Piccadilly Circus":
            #     offset = (0.003, -0.002)
            # elif name == "Leicester Square":
            #     offset = (0.004, -0.002)
            # elif name == "Covent Garden":
            #     offset = (0.005, 0)
            # elif name == "Holborn":
            #     offset = (0.004, -0.002)
            # elif name == "Caledonian Road":
            #     offset = (0.004, 0)
            name = '\n'.join(name.split(' '))
            plt.text(row['Longitude'] + offset[0], row['Latitude'] + offset[1], name, rotation=0, ha='center', va='center',
                    fontsize=8, color='black', fontweight='bold')

        # Draw legend
        for index, row in lines.iterrows():
            plt.plot([], [], color=row['Color'], label=row['Line'], marker='o', markeredgecolor='black', markeredgewidth='1', markersize=10, linewidth=2)
        legend = plt.legend(loc='lower right', fontsize=12, frameon=True, framealpha=1, borderpad=1, prop={'size':10})
        legend.get_frame().set_linewidth(2)

        # Add "Key" text above the legend
        def update_key_position(event):
            legend_bbox = legend.get_window_extent().transformed(self.ax.transData.inverted())
            key_text.set_position(((legend_bbox.x0 + legend_bbox.x1) / 2, legend_bbox.y1 + 0.004))
            self.fig.canvas.draw_idle()

        legend_bbox = legend.get_window_extent().transformed(self.ax.transData.inverted())
        key_text = self.ax.text((legend_bbox.x0 + legend_bbox.x1) / 2, legend_bbox.y1 + 0.004, "Key", fontsize=11, ha='center', va='center', weight='bold')
        self.fig.canvas.mpl_connect('draw_event', update_key_position)
        
        # Set title
        plt.title('Public Transport Network of London', fontsize=30, fontweight='bold')

        # Show plot
        plt.axis('equal')
        # plt.show()
        # return self.fig

# Initialize the Tkinter application
if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkApp(root)
    root.mainloop()
