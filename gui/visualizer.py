import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
from gui.palette import TREE_VISUALIZER_PALETTE
import textwrap


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

    def get_hierarchical_pos(self, G, root, width=1., vert_gap=0.3, vert_loc=0, xcenter=0.5, pos=None, parent=None):
        """
        Calculate hierarchical positions for nodes in a tree graph.

        This method positions nodes in a top-down hierarchical layout, suitable for tree structures.
        It recursively assigns positions starting from the root node, with improved spacing
        to ensure leaf nodes remain readable and non-overlapping.

        Args:
            G (networkx.DiGraph): The directed graph representing the tree.
            root: The root node label to start positioning from.
            width (float): The width allocated for the current subtree. Default is 1.0.
            vert_gap (float): The vertical gap between levels. Default is 0.3.
            vert_loc (float): The vertical location for the current level. Default is 0.
            xcenter (float): The x-center position for the current subtree. Default is 0.5.
            pos (dict): Dictionary to store node positions. If None, a new dict is created.
            parent: The parent node label, used to avoid backtracking in undirected graphs.

        Returns:
            dict: A dictionary mapping node labels to (x, y) positions.
        """
        if pos is None:
            pos = {root: (xcenter, vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)
        
        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if len(children) != 0:
            # Calculate spacing: ensure minimum width per child to prevent overlaps
            min_width = 0.15  # Minimum horizontal space per child node
            calculated_width = max(width / len(children), min_width * len(children))
            dx = calculated_width / len(children) if len(children) > 0 else width
            
            # Center the children under the parent
            total_width = dx * len(children)
            nextx = xcenter - total_width / 2 + dx / 2
            
            for child in children:
                pos = self.get_hierarchical_pos(G, child, width=dx * 0.8, vert_gap=vert_gap,
                                                vert_loc=vert_loc - vert_gap, xcenter=nextx,
                                                pos=pos, parent=root)
                nextx += dx
        
        return pos

    def draw_tree(self, tree_obj):
        """
        Draw and display a tree structure as a hierarchical graph.

        Converts the tree object to a NetworkX graph, applies hierarchical positioning,
        colors nodes based on roles (Attacker/Defender), renders edges with dashed style
        for Defender nodes, and adapts node sizes and text wrapping for labels.
        Embeds the visualization in the parent frame. Cleans up any previous visualization
        before rendering the new one.

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

        # Determine root
        if tree_obj.root is not None:
            root = tree_obj.root.label
        else:
            root = next(iter(G.nodes))

        # Get hierarchical positions
        pos = self.get_hierarchical_pos(G, root)

        # Prepare labels and sizes
        labels = {}
        node_sizes = {}
        for node in tree_obj.nodes:
            wrapped_label = textwrap.fill(str(node.label), width=15)
            labels[node.label] = wrapped_label
            node_sizes[node.label] = max(1000, len(wrapped_label) * 50)

        # Filter to only positioned nodes
        positioned_nodes = list(pos.keys())

        # Create subgraph for positioned nodes
        G_pos = G.subgraph(positioned_nodes)

        # 1. CREIAMO UN DIZIONARIO DI MAPPATURA (Single Source of Truth)
        role_map = {}
        for node in tree_obj.nodes:
            # Estraiamo il ruolo e rimuoviamo spazi/ritorni a capo invisibili
            role_map[node.label] = node.role.strip() if node.role else 'Attacker'

        # 2. ASSEGNAMO I COLORI RISPETTANDO L'ORDINE DI NETWORKX
        node_colors = []
        for node_label in G_pos.nodes():
            role = role_map.get(node_label, 'Attacker')
            if role == 'Defender':
                node_colors.append(TREE_VISUALIZER_PALETTE["defender"])
            elif role == 'Attacker':
                node_colors.append(TREE_VISUALIZER_PALETTE["attacker"])
            else:
                node_colors.append("#808080")

        # 3. DIVIDIAMO GLI ARCHI PER IL TRATTEGGIO DELLA DIFESA
        solid_edges = []
        dashed_edges = []
        for u, v in G_pos.edges():
            target_role = role_map.get(v, 'Attacker')
            if target_role == 'Defender':
                dashed_edges.append((u, v))
            else:
                solid_edges.append((u, v))

        # 4. DISEGNAMO IL GRAFO
        nx.draw_networkx_nodes(G_pos, pos, ax=ax, node_color=node_colors, node_size=1500)
        nx.draw_networkx_edges(G_pos, pos, ax=ax, edgelist=solid_edges, edge_color='gray', arrows=True)
        nx.draw_networkx_edges(G_pos, pos, ax=ax, edgelist=dashed_edges, edge_color='gray', arrows=True, style='dashed')

        # Draw labels
        pos_labels = {node: labels[node] for node in positioned_nodes}
        nx.draw_networkx_labels(G_pos, pos, ax=ax, labels=pos_labels, font_size=8, font_color='white')

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