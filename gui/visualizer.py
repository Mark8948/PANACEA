import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
from gui.palette import TREE_VISUALIZER_PALETTE
import textwrap
import tkinter as tk


class TreeVisualizer:
    """
    Handles visualization of attack-defense trees using Matplotlib and NetworkX.

    This class is responsible for rendering tree structures as interactive graphs,
    with node coloring based on player roles (Attacker/Defender) and hierarchical layouts.
    Supports right-click context menu for pruning and resetting the tree.
    """

    def __init__(self, master_frame, on_prune=None, on_reset=None):
        """
        Initialize a TreeVisualizer instance.

        Args:
            master_frame: The parent Tkinter frame where the visualization will be embedded.
            on_prune (callable): Callback invoked with the node label when the user selects
                                 "Pota da qui" from the context menu. Receives a str argument.
            on_reset (callable): Callback invoked when the user selects "Reimposta albero"
                                 from the context menu. No arguments.
        """
        self.master_frame = master_frame
        self.canvas = None
        self.fig = None
        self.ax = None
        self._pos = {}
        self._context_menu = None
        self._hovered_node = None

        self.on_prune = on_prune
        self.on_reset = on_reset

    def get_hierarchical_pos(self, G, root, width=1., vert_gap=0.3, vert_loc=0, xcenter=0.5, pos=None, parent=None):
        """
        Calculate hierarchical positions for nodes in a tree graph.

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
            min_width = 0.15
            calculated_width = max(width / len(children), min_width * len(children))
            dx = calculated_width / len(children) if len(children) > 0 else width

            total_width = dx * len(children)
            nextx = xcenter - total_width / 2 + dx / 2

            for child in children:
                pos = self.get_hierarchical_pos(G, child, width=dx * 0.8, vert_gap=vert_gap,
                                                vert_loc=vert_loc - vert_gap, xcenter=nextx,
                                                pos=pos, parent=root)
                nextx += dx

        return pos

    def _get_node_at(self, xdata, ydata, threshold=0.05):
        """
        Return the label of the node closest to (xdata, ydata), or None if too far.

        Args:
            xdata (float): X coordinate in data space.
            ydata (float): Y coordinate in data space.
            threshold (float): Maximum distance to consider a hit.

        Returns:
            str or None: The label of the nearest node within threshold, or None.
        """
        closest = None
        min_dist = float("inf")
        for label, (nx_x, ny_y) in self._pos.items():
            dist = ((xdata - nx_x) ** 2 + (ydata - ny_y) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest = label
        if min_dist <= threshold:
            return closest
        return None

    def _show_context_menu(self, event):
        """
        Handle right-click on the Matplotlib canvas.

        Converts the pixel position to data coordinates, finds the nearest node,
        and shows a Tkinter context menu with pruning and reset options.

        Args:
            event: The Matplotlib MouseEvent from the button_press_event.
        """
        if event.inaxes is None or not self._pos:
            return

        node_label = self._get_node_at(event.xdata, event.ydata)

        if self._context_menu:
            try:
                self._context_menu.destroy()
            except Exception:
                pass

        menu = tk.Menu(self.master_frame, tearoff=0, bg="#1A2A3D", fg="#F6F8FB",
                       activebackground="#2F80ED", activeforeground="#F6F8FB",
                       font=("Segoe UI", 11), bd=0, relief="flat")

        if node_label:
            menu.add_command(
                label=f"✂  Prune node ({node_label})",
                command=lambda: self._trigger_prune(node_label)
            )
        else:
            menu.add_command(label="✂  Prune node (no node selected)", state="disabled")

        menu.add_separator()
        menu.add_command(label="↺  Reset tree", command=self._trigger_reset)

        self._context_menu = menu

        # Convert Matplotlib canvas pixel coords to screen coords
        widget = self.canvas.get_tk_widget()
        root_x = widget.winfo_rootx() + int(event.x)
        root_y = widget.winfo_rooty() + int(self.fig.bbox.height - event.y)

        menu.post(root_x, root_y)

    def _trigger_prune(self, node_label):
        """Invoke the on_prune callback with the selected node label."""
        if self.on_prune:
            self.on_prune(node_label)

    def _trigger_reset(self):
        """Invoke the on_reset callback."""
        if self.on_reset:
            self.on_reset()

    def draw_tree(self, tree_obj):
        """
        Draw and display a tree structure as a hierarchical graph.

        Converts the tree object to a NetworkX graph, applies hierarchical positioning,
        colors nodes based on roles (Attacker/Defender), renders edges with dashed style
        for Defender nodes, and adapts node sizes and text wrapping for labels.
        Embeds the visualization in the parent frame. Cleans up any previous visualization
        before rendering the new one. Binds right-click for context menu.

        Args:
            tree_obj: A Tree object containing nodes and edges to visualize.
        """
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            if self.fig is not None:
                plt.close(self.fig)

        G = tree_obj.to_graph()

        self.fig, self.ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor(TREE_VISUALIZER_PALETTE["bg_dark"])
        self.ax.set_facecolor(TREE_VISUALIZER_PALETTE["bg_dark"])

        if tree_obj.root is not None:
            root = tree_obj.root.label
        else:
            root = next(iter(G.nodes))

        pos = self.get_hierarchical_pos(G, root)
        self._pos = pos  # Store for hit-testing

        labels = {}
        node_sizes = {}
        for node in tree_obj.nodes:
            wrapped_label = textwrap.fill(str(node.label), width=15)
            labels[node.label] = wrapped_label
            node_sizes[node.label] = max(1000, len(wrapped_label) * 50)

        positioned_nodes = list(pos.keys())
        G_pos = G.subgraph(positioned_nodes)

        role_map = {}
        for node in tree_obj.nodes:
            role_map[node.label] = node.role.strip() if node.role else 'Attacker'

        node_colors = []
        for node_label in G_pos.nodes():
            role = role_map.get(node_label, 'Attacker')
            if role == 'Defender':
                node_colors.append(TREE_VISUALIZER_PALETTE["defender"])
            elif role == 'Attacker':
                node_colors.append(TREE_VISUALIZER_PALETTE["attacker"])
            else:
                node_colors.append("#808080")

        solid_edges = []
        dashed_edges = []
        for u, v in G_pos.edges():
            target_role = role_map.get(v, 'Attacker')
            if target_role == 'Defender':
                dashed_edges.append((u, v))
            else:
                solid_edges.append((u, v))

        nx.draw_networkx_nodes(G_pos, pos, ax=self.ax, node_color=node_colors, node_size=1500)
        nx.draw_networkx_edges(G_pos, pos, ax=self.ax, edgelist=solid_edges, edge_color='gray', arrows=True)
        nx.draw_networkx_edges(G_pos, pos, ax=self.ax, edgelist=dashed_edges, edge_color='gray', arrows=True, style='dashed')

        pos_labels = {node: labels[node] for node in positioned_nodes}
        nx.draw_networkx_labels(G_pos, pos, ax=self.ax, labels=pos_labels, font_size=8, font_color='white')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master_frame)
        self.canvas.draw()
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid_columnconfigure(0, weight=1)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Bind right-click for context menu
        self.fig.canvas.mpl_connect("button_press_event", lambda e: self._show_context_menu(e) if e.button == 3 else None)

    def cleanup(self):
        """
        Clean up Matplotlib resources and Tkinter callbacks.
        """
        if self._context_menu:
            try:
                self._context_menu.destroy()
            except Exception:
                pass
        self._context_menu = None
        self._pos = {}

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
        self.ax = None