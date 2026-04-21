import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
from gui.palette import TREE_VISUALIZER_PALETTE


class TreeVisualizer:
    """
    Handles visualization of attack-defense trees using Matplotlib and NetworkX.

    This class is responsible for rendering tree structures as interactive graphs,
    with node coloring based on player roles (Attacker/Defender) and hierarchical layouts.
    """

    def __init__(self, master_frame):
        """
        Initialize a TreeVisualizer instance.

        Args:
            master_frame: The parent Tkinter frame where the visualization will be embedded.
        """
        self.master_frame = master_frame
        self.canvas = None
        self.fig = None

    def draw_tree(self, tree_obj):
        """
        Draw and display a tree structure as a hierarchical graph.

        Converts the tree object to a NetworkX graph, applies hierarchical positioning,
        colors nodes based on roles (red for Attacker, green for Defender), and embeds
        the visualization in the parent frame. Cleans up any previous visualization before
        rendering the new one.

        Args:
            tree_obj: A Tree object containing nodes and edges to visualize.
        """
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            if self.fig is not None:
                plt.close(self.fig)

        G = tree_obj.to_graph()

        self.fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor(TREE_VISUALIZER_PALETTE["bg_dark"])
        ax.set_facecolor(TREE_VISUALIZER_PALETTE["bg_dark"])

        try:
            if tree_obj.root is None:
                raise ValueError("Tree root is None")
            pos = tree_obj.hierarchy_pos(G, tree_obj.root.label)
        except Exception:
            pos = nx.spring_layout(G)

        node_colors = []
        for node in G.nodes:
            role = G.nodes[node].get('role', 'Attacker')
            node_colors.append(TREE_VISUALIZER_PALETTE["attacker"] if role == 'Attacker' else TREE_VISUALIZER_PALETTE["defender"])

        nx.draw(G, pos, ax=ax,
                node_color=node_colors,
                with_labels=True,
                arrows=True,
                node_size=1000,
                font_size=8,
                font_color='white',
                edge_color='gray')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master_frame)
        self.canvas.draw()
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid_columnconfigure(0, weight=1)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def cleanup(self):
        """
        Clean up Matplotlib resources and Tkinter callbacks.

        Destroys the canvas widget, closes the Matplotlib figure, and cleans up
        any pending Tkinter callbacks to prevent errors when the application closes.
        """
        if self.canvas:
            try:
                self.canvas.get_tk_widget().destroy()
            except Exception:
                pass
        
        if self.fig is not None:
            try:
                plt.close(self.fig)
            except Exception:
                pass
        
        self.canvas = None
        self.fig = None