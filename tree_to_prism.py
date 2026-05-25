import xml.etree.ElementTree as ET
from tree import Node, Tree

def parse_children(node):
    children = []
    for child in node:
        if child.tag == 'node':
            children.append(child)
    return children

def parse_node(node):
    refinement = node.attrib['refinement']
    label = node.find('label').text.replace(" ", "")
    try:
        comment = node.find('comment').text
    except AttributeError:
        comment = ""
    return Node(label, refinement, comment)

def parse_file(file):
    xml = ET.parse(file)
    r = xml.find('node')
    root = parse_node(r)
    
    tree = Tree()
    queue = [(root, r)]

    while queue:
        parent_node, parent = queue.pop()
        tree.add_node(parent_node)
        
        children = parse_children(parent)
        for child in children:
            child_node = parse_node(child)
            queue = [(child_node, child)] + queue
            tree.add_edge(parent_node, child_node)
            
    return tree

def get_info(df):
    goal = df.loc[df["Type"] == "Goal"]["Label"].values[0]
    actions_to_goal = set(df.loc[df["Parent"] == goal]["Action"].values)
    actions_to_goal = {a for a in actions_to_goal if a != ""}

    df_attacker = df.loc[df["Role"] == "Attacker"]
    df_attacker = df_attacker.loc[df_attacker["Type"] != "Goal"]
    df_defender = df.loc[df["Role"] == "Defender"]

    initial_attributes = df_attacker.loc[df_attacker["Action"] == ""]["Label"].to_list()
    for row in df_attacker.loc[df_attacker["Action"] == ""]["Label"].to_list():
        children = df.loc[df["Label"] == row]["Children"].values
        children = [c for sets in children for c in sets]
        for child in children:
            if child in df_attacker["Label"].values and row in initial_attributes:
                initial_attributes.remove(row)

    df_attacker = df_attacker.loc[~df_attacker["Label"].isin(initial_attributes)]

    attacker_actions = {}
    defender_actions = {}
    
    for _, row in df.iterrows():
        action = row["Action"]
        if action == "":
            continue
        
        parent_label = row["Parent"]
        parent_type = df.loc[df["Label"] == parent_label]["Type"].values[0]
        
        # FIX LOGICO 1: Gestione dell'annidamento Azione->Azione. 
        # Se il genitore è un'Azione, l'effetto dell'azione corrente è soddisfare se stessa,
        # in modo che il genitore possa vederla completata.
        if parent_type in ["Attribute", "Goal"]:
            effect = parent_label
        else:
            effect = row["Label"] 
            
        cost = row["Cost"]
        
        # FIX LOGICO 2: Usiamo la regola logica (AND/OR) del nodo stesso, non del genitore!
        refinement = row["Refinement"] 
        
        time = row["Time"]
        preconditions = row["Children"]
        
        preconditions = [p for p in preconditions if row["Role"]==df.loc[df["Label"] == p]["Role"].values[0]]

        if row["Role"] == "Attacker" and action not in attacker_actions:
            preconditions = [p for p in preconditions if p not in df_defender["Label"].values]
            attacker_actions[action] = {
                "preconditions" : preconditions, 
                "effect" : effect, 
                "cost" : cost,
                "time" : time,
                "refinement" : refinement}
        elif action in attacker_actions.keys():
            attacker_actions[action]["preconditions"] += preconditions
        elif row["Role"] == "Defender" and action not in defender_actions:
                defender_actions[action] = {
                    "preconditions" : preconditions, 
                    "effect" : effect, 
                    "cost" : cost,
                    "time" : time,
                    "refinement" : refinement}
                
    return goal, actions_to_goal, initial_attributes, attacker_actions, defender_actions, df_attacker, df_defender

def get_prism_model(tree):
    df = tree.to_dataframe()
    goal, actions_to_goal, initial_attributes, attacker_actions, defender_actions, df_attacker, df_defender = get_info(df)
    
    text = "smg\n\nplayer attacker\n\tattacker"
    att_actions = [f"[{a}]" for a in attacker_actions.keys()]
    if att_actions:
        text += ", " + ", ".join(att_actions)
    text += "\nendplayer\n"

    text += "player defender\n\tdefender, [passD]"
    def_actions = [f"[{a}]" for a in defender_actions.keys()]
    if def_actions:
        text += ", " + ", ".join(def_actions)
    text += "\nendplayer\n\nglobal sched : [1..2];\n\n"

    # --- INIZIO FIX: DICHIARAZIONE DINAMICA E SICURA DELLE VARIABILI GLOBALI ---
    text += f'global {goal} : [0..1];\nlabel "terminate" = {goal}=1;\n\n'

    defender_attributes = set(df_defender.loc[df_defender["Type"] == "Attribute"]["Label"].values)
    attacker_attributes = set(df_attacker.loc[df_attacker["Type"] == "Attribute"]["Label"].values)
    
    declared_vars = {goal}
    
    for a in attacker_attributes:
        if a not in declared_vars:
            text += f"global {a} : [0..2];\n"
            declared_vars.add(a)
            
    for a in set(initial_attributes):
        if a not in declared_vars:
            text += f"global {a} : [1..2];\n"
            declared_vars.add(a)
            
    # Raccogliamo TUTTI gli effetti e precondizioni usati nelle azioni
    all_implicit_vars = set()
    for act in attacker_actions.values():
        all_implicit_vars.add(act["effect"])
        all_implicit_vars.update(act["preconditions"])
    for act in defender_actions.values():
        all_implicit_vars.add(act["effect"])
        all_implicit_vars.update(act["preconditions"])
        
    # Dichiariamo quelli mancanti (evitando le variabili locali del difensore)
    for var in all_implicit_vars:
        if var not in declared_vars and var not in defender_attributes:
            text += f"global {var} : [0..2];\n"
            declared_vars.add(var)
    # --- FINE FIX ---

    text += "\nmodule attacker\n\n"
    
    for a in attacker_actions.keys():
        text += f"\tprogress_{a} : bool;\n"
        
    text += "\n"

    for a in attacker_actions.keys():
        preconditions = attacker_actions[a]["preconditions"]
        effect = attacker_actions[a]["effect"]
        effects = f"({effect}'=1)"
        if attacker_actions[a]["refinement"] == "disjunctive":
            refinement = "|"
        else:
            refinement = "&"
            
        precon = ""
        if preconditions != []:
            precon += " & ("
            for p in set(preconditions):
                precon += f"{p}=1 {refinement} "
            precon = f"{precon[:-3]})"
            
        text += f"\t[{a}] sched=1 & {goal}!=1 & {effect}=0 & !progress_{a}{precon} -> {effects} & (progress_{a}'=true) & (sched'=2);\n"
        
    text += "\nendmodule\n\nmodule defender\n\n"

    for a in defender_attributes:
        text += f"\t{a} : [0..1];\n"
        
    text += "\n"
        
    for a in defender_actions.keys():
        preconditions = defender_actions[a]["preconditions"]
        effect = defender_actions[a]["effect"]
        if defender_actions[a]["refinement"] == "disjunctive":
            refinement = "|"
        else:
            refinement = "&"
            
        precon = ""
        if preconditions != []:
            precon += " & ("
            for p in set(preconditions):
                precon += f"{p}=1 {refinement} "
            precon = f"{precon[:-3]})"

        if effect in defender_attributes:
            text += f"\t[{a}] sched=2 & {goal}!=1 & {effect}=0{precon} -> ({effect}'=1) & (sched'=1);\n"
        else:
            text += f"\t[{a}] sched=2 & {goal}!=1 & {effect}!=2{precon} -> ({effect}'=2) & (sched'=1);\n"
            
    text += "\n\t// Azione pass-turn per impedire blocchi dello scheduler (deadlock)\n"
    text += "\t[passD] sched=2 -> (sched'=1);\n"
        
    text += '\nendmodule\n\nrewards "attacker"\n\n'

    for a in attacker_actions.keys():
        text += f"\t[{a}] true : {attacker_actions[a]['cost']};\n"
        
    text += '\nendrewards\n\nrewards "defender"\n\n'

    for a in actions_to_goal:
        text += f"\t[{a}] true : {int(attacker_actions[a]['cost'])*10};\n"
    for a in defender_actions.keys():
        text += f"\t[{a}] true : {defender_actions[a]['cost']};\n"
          
    text += "\nendrewards"

    return text

def get_prism_model_time(tree):
    df = tree.to_dataframe()
    goal, actions_to_goal, initial_attributes, attacker_actions, defender_actions, df_attacker, df_defender = get_info(df)
    
    attacker_max_time = max(int(x) for x in df_attacker["Time"].values if str(x).isdigit()) if not df_attacker.empty else 1
    defender_max_time = max(int(x) for x in df_defender["Time"].values if str(x).isdigit()) if not df_defender.empty else 1
    
    text = "smg\n\nplayer attacker\n\tattacker, [wait1], [passA]"
    att_actions = []
    for a in attacker_actions.keys():
        att_actions.extend([f"[start{a}]", f"[end{a}]", f"[fail{a}]"])
    if att_actions:
        text += ", " + ", ".join(att_actions)
    text += "\nendplayer\n"

    text += "player defender\n\tdefender, [wait2], [passD]"
    def_actions = []
    for a in defender_actions.keys():
        def_actions.extend([f"[start{a}]", f"[end{a}]"])
    if def_actions:
        text += ", " + ", ".join(def_actions)
    text += "\nendplayer\n\nglobal sched : [1..2];\n\n"

    # --- INIZIO FIX: DICHIARAZIONE DINAMICA E SICURA DELLE VARIABILI GLOBALI ---
    text += f'global {goal} : [0..1];\nlabel "terminate" = {goal}=1;\n\n'

    defender_attributes = set(df_defender.loc[df_defender["Type"] == "Attribute"]["Label"].values)
    attacker_attributes = set(df_attacker.loc[df_attacker["Type"] == "Attribute"]["Label"].values)
    
    declared_vars = {goal}
    
    for a in attacker_attributes:
        if a not in declared_vars:
            text += f"global {a} : [0..2];\n"
            declared_vars.add(a)
            
    for a in set(initial_attributes):
        if a not in declared_vars:
            text += f"global {a} : [1..2];\n"
            declared_vars.add(a)
            
    all_implicit_vars = set()
    for act in attacker_actions.values():
        all_implicit_vars.add(act["effect"])
        all_implicit_vars.update(act["preconditions"])
    for act in defender_actions.values():
        all_implicit_vars.add(act["effect"])
        all_implicit_vars.update(act["preconditions"])
        
    for var in all_implicit_vars:
        if var not in declared_vars and var not in defender_attributes:
            text += f"global {var} : [0..2];\n"
            declared_vars.add(var)
    # --- FINE FIX ---

    text += "\nmodule attacker\n\n"

    for a in attacker_actions.keys():
        text += f"\tprogress_{a} : bool;\n"
        
    text += "\n"
    text += f"\ttime1 : [-1..{attacker_max_time}];\n"
    text += f"\t[wait1] sched=1 & time1>0 -> (sched'=2) & (time1'=time1-1);\n"
    text += "\t[passA] sched=1 & time1<0 -> (sched'=2);\n"

    for a in attacker_actions.keys():
        preconditions = attacker_actions[a]["preconditions"]
        effect = attacker_actions[a]["effect"]
        effects = f"({effect}'=1)"
        time = attacker_actions[a]["time"]
        
        if attacker_actions[a]["refinement"] == "disjunctive":
            refinement = "|"
            fail_refinement = "&"
        else:
            refinement = "&"
            fail_refinement = "|"
        
        precon = ""
        fail = ""
        if preconditions != []:
            precon += " & ("
            fail += " | "
            for p in set(preconditions):
                precon += f"{p}=1 {refinement} "
                fail += f"{p}!=1 {fail_refinement} " 
            precon = f"{precon[:-3]})"
            fail = f"{fail[:-3]}"
            
        text += f"\n\t[start{a}] sched=1 & time1<0 & !progress_{a} & {goal}!=1 & {effect}=0{precon} -> (sched'=2) & (time1'={time}) & (progress_{a}'=true);\n"
        text += f"\t[end{a}] sched=1 & time1=0 & progress_{a} & {goal}!=1 & {effect}=0{precon} -> (time1'=time1-1) & (progress_{a}'=false) & {effects};\n"
        text += f"\t[fail{a}] sched=1 & time1=0 & progress_{a} & {goal}!=1 & ({effect}!=0 {fail}) -> (time1'=time1-1) & (progress_{a}'=false);\n"
        
    text += "\nendmodule\n\nmodule defender\n\n"

    for a in defender_attributes:
        text += f"\t{a} : [0..1];\n"
    
    text += "\n"
    for a in defender_actions.keys():
        text += f"\tprogress_{a} : bool;\n"
        
    text += f"\n\ttime2 : [-1..{defender_max_time}];\n"
    text += f"\t[wait2] sched=2 & time2>0 -> (sched'=1) & (time2'=time2-1);\n"
    text += "\t[passD] sched=2 & time2<0 -> (sched'=1);\n"
        
    for a in defender_actions.keys():
        preconditions = defender_actions[a]["preconditions"]
        effect = defender_actions[a]["effect"]
        time = defender_actions[a]["time"]
        
        if defender_actions[a]["refinement"] == "disjunctive":
            refinement = "|"
        else:
            refinement = "&"
            
        precon = ""
        if preconditions != []:
            precon += " & ("
            for p in set(preconditions):
                precon += f"{p}=1 {refinement} "
            precon = f"{precon[:-3]})"

        if effect in defender_attributes:
            text += f"\n\t[start{a}] sched=2 & time2<0 & !progress_{a} & {goal}!=1 & {effect}=0{precon} -> (sched'=1) & (time2'={time}) & (progress_{a}'=true);\n"
            text += f"\t[end{a}] sched=2 & time2=0 & progress_{a} & {goal}!=1 & {effect}=0{precon} -> (time2'=time2-1) & (progress_{a}'=false) & ({effect}'=1);\n"
        else:
            text += f"\n\t[start{a}] sched=2 & time2<0 & !progress_{a} & {goal}!=1 & {effect}!=2{precon} -> (sched'=1) & (time2'={time}) & (progress_{a}'=true);\n"
            text += f"\t[end{a}] sched=2 & time2=0 & progress_{a} & {goal}!=1 & {effect}!=2{precon} -> (time2'=time2-1) & (progress_{a}'=false) & ({effect}'=2);\n"
        
    text += '\nendmodule\n\nrewards "attacker"\n\n'

    for a in attacker_actions.keys():
        text += f"\t[start{a}] true : {attacker_actions[a]['time']};\n"
        
    text += '\nendrewards\n\nrewards "defender"\n\n'

    for a in actions_to_goal:
        text += f"\t[end{a}] true : {int(attacker_actions[a]['time'])*10};\n"
    for a in defender_actions.keys():
        text += f"\t[start{a}] true : {defender_actions[a]['time']};\n"
          
    text += "\nendrewards"

    return text

def save_prism_model(prism_model, file):
    with open(file, 'w') as f:
        f.write(prism_model)
    
def save_prism_properties(file, mode="cost"):
    with open(file, 'w') as f:
        f.write('// Minimum expected value for the attacker\n')
        f.write('<<attacker>>R{"attacker"}min=? [ F "terminate" ];\n\n')

        f.write('// Minimum expected value for the defender\n')
        f.write('<<defender>>R{"defender"}min=? [ F "terminate" ];\n')