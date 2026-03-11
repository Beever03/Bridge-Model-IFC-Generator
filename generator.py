import ifcopenshell
from ifcopenshell.api import run

def main(params: dict) -> str:
    #1).BASIC PARAMETERS
    BRIDGE_NAME = str(params.get("bridge_name", "MyBridge"))
    OUT_PATH = BRIDGE_NAME if BRIDGE_NAME.lower().endswith(".ifc") else BRIDGE_NAME + ".ifc"

    #deck
    deck_length = float(params.get("deck_length", 40))
    deck_width = float(params.get("deck_width", 6))
    deck_thickness = float(params.get("deck_thickness", 0.8))
    deck_height_above_ground = float(params.get("deck_height_above_ground", 5)) #elevation off ground

    #Pier, add if statement for values that exceeds the value of deck
    pier_width = float(params.get("pier_width", 2))
    pier_depth = float(params.get("pier_depth", 2))
    pier_height = deck_height_above_ground  #Assuming pier supports the deck directly
    pier_y = deck_width/2.0

    #Pier locations along the deck
    pier_spacing = float(params.get("pier_spacing",10))
    pier_edge_clear = float(params.get("pier_edge_clear", 5)) #5 meters off from the edge

    #Superstructure details, add if statement for values that exceeds the value of deck
    #Girder
    girder_width = float(params.get("girder_width",0.35))
    girder_depth = float(params.get("girder_depth", 1.5))
    girder_spacing = float(params.get("girder_spacing", 1.0))

    girder_combo = girder_width + girder_spacing
    girder_count = int(deck_width/girder_combo) + 1

    #Crossbeam, add if statement for values that exceeds the value of deck
    crossbeam_width = float(params.get("crossbeam_width",0.25))
    crossbeam_depth = float(params.get("crossbeam_depth",0.6))
    crossbeam_spacing = float(params.get("crossbeam_spacing",4))

    #2).CREATE A NEW IFC FILE
    # #IFC4X3is where IfcBridge/IfcBridgePart are standard
    model = run("project.create_file", version = "IFC4X3")
    #Every model needs exactly one IfcProject
    project = run("root.create_entity", model, ifc_class = "IfcProject", name = "Demo Project")

    #Assign metric unit
    run(
        "unit.assign_unit",
        model,
        length={
            "is_metric": True,
            "raw": "METER"
        },
    )

    #3). Geometry context: so we can store 3D shape
    context = run("context.add_context", model, context_type="Model")
    body = run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )

    #4). Spatial structure: site -> bridge -> bridge part


    site = run( "root.create_entity", model, ifc_class = "IfcSite", name ="site" )
    bridge = run( "root.create_entity", model, ifc_class = "IfcBridge", name = BRIDGE_NAME )

    superstructure = run(
        "root.create_entity",
        model,
        ifc_class = "IfcBridgePart",
        name = "Superstructure",
        predefined_type = "SUPERSTRUCTURE",
    )

    substructure = run(
        "root.create_entity",
        model,
        ifc_class = "IfcBridgePart",
        name = "Substructure",
        predefined_type = "SUBSTRUCTURE",
    )


    #Arrange them in hierachy
    run("aggregate.assign_object", model, relating_object = project, products = [site])
    run("aggregate.assign_object", model, relating_object = site, products = [bridge])
    run("aggregate.assign_object", model, relating_object = bridge, products = [superstructure, substructure])


    #5). Functions set up

    #placing the element:
    def place(product, matrix):
        run("geometry.edit_object_placement", model, product = product, matrix = matrix)

    #create rectangles for column/volumn
    def make_rect_profile(profile_name, xdim, ydim):
        return model.create_entity(
            "IfcRectangleProfileDef",
            ProfileType = "AREA",
            ProfileName = profile_name,
            XDim = float(xdim),
            YDim = float(ydim),
        )

    #volumize rectangles
    def assign_extrusion(product, profile, depth):
        repr_ = run(
            "geometry.add_profile_representation",
            model,
            context = body,
            profile = profile,
            depth = float(depth),
        )
        run("geometry.assign_representation", model, product = product, representation = repr_ )
        return repr_

    def make_block_proxy(name, xdim, ydim, zdim, placement_matrix):
        p = run("root.create_entity", model, ifc_class = "IfcBuildingElementProxy", name = name)
        place(p, placement_matrix)
        prof = make_rect_profile(f"{name}_profile", xdim, ydim)
        assign_extrusion(p, prof, zdim)
        return p

    #6). Create the deck as a slab (rectangular footprint extruded by thickness)
    deck = run(
        "root.create_entity", 
        model,
        ifc_class = "IfcSlab", 
        name= "Deck", 
        predefined_type = "FLOOR"
    )

    place(deck,[
        [1,0,0,0.0],      #x-axis + x translation
        [0,1,0,0.0],      #y-axis + y translation
        [0,0,1,deck_height_above_ground],   #z-axis + z translation
        [0,0,0,1],    
    ])      

    #Slab footprint parameter is in the slab's LOCAL XY-plane
    #Define a rectangle going around and returning to the start point:
    deck_polyline = [
        (0.0, 0.0),
        (deck_length, 0.0),
        (deck_length, deck_width),
        (0.0, deck_width),
        (0.0,0.0),
    ]

    deck_repr = run("geometry.add_slab_representation",
                    model,
                    context = body,
                    depth = deck_thickness,
                    polyline = deck_polyline,
    )

    #Assigning actual representation to the deck
    run("geometry.assign_representation", model, product = deck, representation = deck_repr)
    #Put the deck inside the bridge part (spatial containment)
    run("spatial.assign_container", model, relating_structure = superstructure, products=[deck])


    #7). Make girders
    girder_profile = make_rect_profile("Girder_Profile", girder_width, girder_depth)  

    def make_girder(name:str, y_centre: float):
        beam = run("root.create_entity", model, ifc_class = "IfcBeam", name = name)
        z_under_deck = deck_height_above_ground - girder_depth/2

        place(beam, [
            [0,0,1,0.0],            #rotation
            [1,0,0,y_centre],       #move sideways
            [0,1,0,z_under_deck],   #move up
            [0,0,0,1],
        ])

        assign_extrusion(beam, girder_profile, deck_length)

        run("spatial.assign_container", model, relating_structure = superstructure, products = [beam])
    
        return beam

    #Plae girders across the width equally
    #Place the first girder in the middle
    girder_ys = []
    if girder_count == 1:
        girder_ys = [deck_width/2.0]

    else:
        #evenly spaced across the deck width
        #girder edge margin = 0.6m, the distance away from both sides of the deck,
        margin = 0.6 
        usable = deck_width - 2 * margin
        girder_ys = [
            margin + i * (usable / (girder_count - 1))
            for i in range(girder_count)
        ]

    for i, gy in enumerate(girder_ys, start = 1):
        make_girder(f"Girder_{i}", gy)


    #8. Piers
    def make_pier(name: str, x: float, y: float):
        pier = run("root.create_entity", model, ifc_class = "IfcColumn", name = name)

        #Place the pier so its local origin is at (x, y, 0)
        place(pier, [
            [1,0,0,x],    # ← arg 2
            [0,1,0,y],    # ← arg 3
            [0,0,1,0.0],  # ← arg 4
            [0,0,0,1],
        ])

        # Create a rectangle profile and set its size
        prof = make_rect_profile(f"{name}_Profile", pier_width, pier_depth)

        # Extrude that profile by pier_height and assign the 3D representation to the tag
        assign_extrusion(pier, prof, pier_height)

        #Relating pier to the bridge part
        run("spatial.assign_container", model, relating_structure=substructure, products = [pier])
        return pier
    
    start_x = pier_edge_clear
    end_x = deck_length - pier_edge_clear

    pier_xs = []
    if end_x <= start_x: #deck to short -> put at least 1 pier in the middle
        pier_xs = [deck_length/2.0]

    else:
        x = start_x
        while x <= end_x + 1e-9 :
            pier_xs.append(x)
            x += pier_spacing

    for idx, px in enumerate (pier_xs, start = 1):
        make_pier(f"Pier_{idx}", px, pier_y)


    #9). Cross beams (IfcBeam running across width)

    def make_crossbeam(name, x_pos):
        beam = run("root.create_entity", model, ifc_class = "IfcBeam", name = name)
        #polyline-profile
        crossbeam_profile = make_rect_profile(f"{name}_Profile", crossbeam_width, crossbeam_depth)

        z_under_deck = deck_height_above_ground - crossbeam_depth/2

        place(beam, [
            [1,0,0, x_pos],         # local X -> global X (translation in X is straightforward here)
            [0,0,1,0],             # local Y -> global Z
            [0,1,0,z_under_deck],  # local Z -> global Y
            [0,0,0,1],
        ])
    
        #extrusion
        assign_extrusion(beam, crossbeam_profile, deck_width)
        run("spatial.assign_container", model, relating_structure = superstructure, products = [beam])
        
        return beam

    start_x = crossbeam_width/2
    end_x = deck_length - crossbeam_width/2

    x = start_x
    idx = 1
    #Use while loop to keep on adding crossbeam until reachs end_x
    while x <= end_x:
        make_crossbeam(f"CrossBeam_{idx}", x)
        x += crossbeam_spacing
        idx += 1

    #10). Save the model
    model.write(OUT_PATH)
    return OUT_PATH

if __name__ == "__main__":
    # Quick local test
    demo = {}
    print("Created:", main(demo))














































































































































