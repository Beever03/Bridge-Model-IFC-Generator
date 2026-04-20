import ifcopenshell
from ifcopenshell.api import run

def main(params: dict) -> str:
    #1).BASIC PARAMETERS
    # Bridge name input, use default if not provided
    BRIDGE_NAME = str(params.get("bridge_name", "MyBridge"))
    # Save the file in .ifc format using the name provided
    OUT_PATH = BRIDGE_NAME if BRIDGE_NAME.lower().endswith(".ifc") else BRIDGE_NAME + ".ifc"

    # Deck parameters input, use default if not provided
    deck_length = float(params.get("deck_length", 40))
    deck_width = float(params.get("deck_width", 6))
    deck_thickness = float(params.get("deck_thickness", 0.8))
    deck_height_above_ground = float(params.get("deck_height_above_ground", 5)) #elevation off ground

    # Pier parameters input, use default if not provided
    pier_width = float(params.get("pier_width", 2))
    pier_depth = float(params.get("pier_depth", 2))
    pier_height = deck_height_above_ground  #Assuming pier supports the deck directly
    pier_y = deck_width/2.0 #Place pier in the middle of the deck width

    # Pier locations along the deck
    pier_number = int(params.get("pier_number", 3))
    pier_edge_clear = float(params.get("pier_edge_clear", 5)) #5 meters off from the edge

    # Girder parameters input, use default if not provided
    girder_width = float(params.get("girder_width", 0.35))
    girder_depth = float(params.get("girder_depth", 1.5))
    girder_number = int(params.get("girder_number", 5))

    # Crossbeam parameters input, use default if not provided
    crossbeam_width = float(params.get("crossbeam_width",0.25))
    crossbeam_depth = float(params.get("crossbeam_depth",0.6))
    crossbeam_number = int(params.get("crossbeam_number", 6))

    # Barrier parameters input, use default if not provided
    barrier_height = float(params.get("barrier_height", 1.2))
    barrier_thickness = float(params.get("barrier_thickness", 0.2))
    barrier_offset = float(params.get("barrier_offset", 0.1))

    #2).CREATE A NEW IFC FILE
    # IFC4X3 is the only IFC version that have IfcBridge/IfcBridgePart
    model = run("project.create_file", version = "IFC4X3")
    #Every model needs exactly one IfcProject
    project = run("root.create_entity", model, ifc_class = "IfcProject", name = "Demo Project")

    # Assign metric unit
    run(
        "unit.assign_unit",
        model,
        length={
            "is_metric": True,
            "raw": "METER"
        },
    )

    #3). Define geometric representation contexts for storing 3D model geometry

    # Create the  main model context
    context = run("context.add_context", model, context_type="Model")

    # Create the body context to store detail
    # This is used to store the physical 3D shape representation of bridge elements
    body = run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )

    #4). Spatial structure: project -> site -> bridge

    # Create site and bridge entities
    site = run( "root.create_entity", model, ifc_class = "IfcSite", name ="site" )
    bridge = run( "root.create_entity", model, ifc_class = "IfcBridge", name = BRIDGE_NAME )

    # Arrange them in hierachy, project contains site, and site contains bridge
    run("aggregate.assign_object", model, relating_object = project, products = [site])
    run("aggregate.assign_object", model, relating_object = site, products = [bridge])

    #5). Functions set up

    # Object placement function:
    def place(product, matrix):
        # Use the built-in object placement function within the 'model', place selected 'product' in pre-defined 'matrix'
        run("geometry.edit_object_placement", model, product = product, matrix = matrix)

    # Place the bridge at the global origin
    place(bridge, [
        [1,0,0, 0.0],
        [0,1,0, 0.0],
        [0,0,1, 0.0],
        [0,0,0, 1],
    ]) 

    # Create rectangles for column/volumn
    def make_rect_profile(profile_name, xdim, ydim):

        # Use the built-in rectangle creation function to create rectangular profile and define each parameters using the values provided
        return model.create_entity(
            "IfcRectangleProfileDef",
            ProfileType = "AREA",
            ProfileName = profile_name,
            XDim = float(xdim),
            YDim = float(ydim),
        )

    # Generate 3D geometry by extruding a 2D profile and assign it to the element
    def assign_extrusion(product, profile, depth):

        # Create a 3D representation by extruding the given 2D profile along its local axis
        repr_ = run(
            "geometry.add_profile_representation",
            model,
            context = body,
            profile = profile,
            depth = float(depth),
        )

        # Assign the generated geometric representation to the IFC element
        run("geometry.assign_representation", model, product = product, representation = repr_ )

        return repr_

    #6). Create the deck as a slab (rectangular footprint extruded by thickness)

    # Create bridge entity and define it as IfcSlab
    deck = run(
        "root.create_entity", 
        model,
        ifc_class = "IfcSlab", 
        name= "Deck", 
        predefined_type = "FLOOR"
    )

    # Call placement function to place the bridge deck
    place(deck,[
        [1,0,0,0.0],      # x-axis + x translation
        [0,1,0,0.0],      # y-axis + y translation
        [0,0,1,deck_height_above_ground],   # z-axis + z translation
        [0,0,0,1],    
    ])      

    # Slab footprint parameter is in the slab's LOCAL XY-plane
    # Define a rectangle going around and returning to the start point:
    deck_polyline = [
        (0.0, 0.0),
        (deck_length, 0.0),
        (deck_length, deck_width),
        (0.0, deck_width),
        (0.0,0.0),
    ]

    # Create 3D geometry for bridge deck using its profile and deck thickness
    deck_repr = run("geometry.add_slab_representation",
                    model,
                    context = body,
                    depth = deck_thickness,
                    polyline = deck_polyline,
    )

    # Assigning actual representation to the deck
    run("geometry.assign_representation", model, product = deck, representation = deck_repr)

    # Put the deck inside the bridge(spatial containment)
    run("spatial.assign_container", model, relating_structure = bridge, products=[deck])


    #7). Make girders

    # Call rectangular profile creation function to create profile for girder
    girder_profile = make_rect_profile("Girder_Profile", girder_width, girder_depth)  

    # Create a function to make girders
    def make_girder(name:str, y_centre: float):
        # Create entity for beam(girder)
        beam = run("root.create_entity", model, ifc_class = "IfcBeam", name = name)

        # Z-position equals to the deck elevation from ground minus half of the girder depth as IFC places object from its centre
        z_under_deck = deck_height_above_ground - girder_depth/2

        # Call placement function to place girders
        # The local axes are rotated so the girder extrusion runs along the bridge length,
        # while the translation terms place it across the deck width and below the deck
        place(beam, [
            [0,0,1,0.0],           # local X aligned with global Z
            [1,0,0,y_centre],      # local Y aligned with global X (positions girder across deck width)
            [0,1,0,z_under_deck],  # local Z aligned with global Y (sets elevation below deck)
            [0,0,0,1],
        ])

        # Create 3D geometry from the girder profile and deck length
        assign_extrusion(beam, girder_profile, deck_length)

        # Relating girder to the bridge
        run("spatial.assign_container", model, relating_structure = bridge, products = [beam])
        
        return beam
    
    # Create an empty list to store the y-positions of the girders
    girder_ys = []

    # If there is only one girder, place it at the centre of the deck width
    if girder_number <= 1:
        girder_ys = [deck_width / 2.0]

    # Otherwise, place the first and last girders aligned with the deck edges in the y-direction
    else:
        # IFC places the girder using its centre point, so half the girder width is used
        # to align the outer face of the girder with the deck edge
        first_y = girder_width / 2.0
        last_y = deck_width - girder_width / 2.0

        # Calculate the centre-to-centre spacing by dividing the distance between
        # the two outermost girders by the number of intervals (girder_number - 1)
        girder_spacing = (last_y - first_y) / (girder_number - 1)

        # Append the y-position of each girder to the list using the calculated spacing
        for i in range(girder_number):
            girder_ys.append(first_y + i * girder_spacing)

    # Create girders using the calculated y-positions
    for i, gy in enumerate(girder_ys, start=1):
        make_girder(f"Girder_{i}", gy)


    #8). Piers

    # create a function to make piers
    def make_pier(name: str, x: float, y: float):

        # Create entity for pier, defined as IfcColumn
        pier = run("root.create_entity", model, ifc_class = "IfcColumn", name = name)

        #Place the pier so its local origin is at (x, y, 0)
        place(pier, [
            [1,0,0,x],   
            [0,1,0,y],    
            [0,0,1,0.0], 
            [0,0,0,1],
        ])

        # Create a rectangle profile and set its size
        prof = make_rect_profile(f"{name}_Profile", pier_width, pier_depth)

        # Create 3D geometry using profile and pier_height
        assign_extrusion(pier, prof, pier_height)

        # Relating pier to the bridge
        run("spatial.assign_container", model, relating_structure= bridge, products = [pier])

        return pier
    
    # Store the x-positions of the piers
    pier_xs = []

    # Define the first and last pier positions based on edge clearance
    first_x = pier_edge_clear
    last_x = deck_length - pier_edge_clear

    # If only one pier is required, place it at the centre of the deck length
    if pier_number <= 1:
        pier_xs = [deck_length / 2.0]

    # If the available span is too short, also place one pier at the centre
    elif last_x <= first_x:
        pier_xs = [deck_length / 2.0]

    # Otherwise, distribute the piers evenly between the two edge clearances
    else:
        pier_spacing = (last_x - first_x) / (pier_number - 1)

        for i in range(pier_number):
            pier_xs.append(first_x + i * pier_spacing)

    # Create piers at the calculated x-positions
    for i, px in enumerate(pier_xs, start=1):
        make_pier(f"Pier_{i}", px, pier_y)


    #9). Cross beams (IfcBeam running across width)

    # Create a function to make crossbeam
    def make_crossbeam(name, x_pos):

        # Create entity for beam(crossbeam)
        beam = run("root.create_entity", model, ifc_class = "IfcBeam", name = name)

        # Create 2D profile for crossbeam
        crossbeam_profile = make_rect_profile(f"{name}_Profile", crossbeam_width, crossbeam_depth)

        # Z-position equals to the elevation of deck above ground minus half of crossbeam depth, note IFC place an object from its centre
        z_under_deck = deck_height_above_ground - crossbeam_depth/2

        # Call placement function to place crossbeam
        # The local axes are rotated so the crossbeam extrusion runs across the deck width,
        # while the translation terms place it along the bridge length and below the deck
        place(beam, [
            [1,0,0, x_pos],        # local X -> global X, position crossbeam across deck length
            [0,0,1,0],             # local Y -> global Z, rotates crossbeam orientation 
            [0,1,0,z_under_deck],  # local Z -> global Y, sets elevation below deck
            [0,0,0,1],
        ])
    
        # Create 3D geomtry using the crossbeam profile created and deck width
        assign_extrusion(beam, crossbeam_profile, deck_width)

        # Relating crossbeam to bridge
        run("spatial.assign_container", model, relating_structure = bridge, products = [beam])
        
        return beam
    
    # Store the x-positions of the crossbeams
    crossbeam_xs = []

    # If only one crossbeam is required, place it at the centre of the deck length
    if crossbeam_number <= 1:
        crossbeam_xs = [deck_length / 2.0]

    # Otherwise, distribute the crossbeams evenly along the deck length
    else:
        # Use half the crossbeam width so the outer crossbeams align with both deck ends
        first_x = crossbeam_width / 2.0
        last_x = deck_length - crossbeam_width / 2.0

        # Compute the centre-to-centre spacing between crossbeams
        crossbeam_spacing = (last_x - first_x) / (crossbeam_number - 1)

        # Generate x-positions for all crossbeams
        for i in range(crossbeam_number):
            crossbeam_xs.append(first_x + i * crossbeam_spacing)

    # Create crossbeams at the calculated x-positions
    for i, cx in enumerate(crossbeam_xs, start=1):
        make_crossbeam(f"CrossBeam_{i}", cx)

    #10). Bridge side barriers 

    # Create a function to make barriers
    def make_barrier(name: str, y_pos: float):

        # Create entity for beam(barrier)
        barrier = run("root.create_entity", model, ifc_class="IfcBeam", name=name)

        z_pos = deck_height_above_ground + deck_thickness + barrier_height/2

       # The local axes are rotated so the barrier extrusion runs along the bridge length,
       # while the translation terms place it across the deck width and above the deck surface
        place(barrier, [
            [0,0,1,0.0],        # local X -> global Z, rotates barrier to align along bridge length
            [1,0,0,y_pos],      # local Y -> global X, positions barrier across deck width
            [0,1,0,z_pos],      # local Z -> global Y, sets elevation above deck surface
            [0,0,0,1],
        ])

        # Create rectangular profile using barrier thickness and height
        barrier_profile = make_rect_profile(f"{name}_Profile", barrier_thickness, barrier_height)

        # Create 3D geomtry using barrier profile and deck length
        assign_extrusion(barrier, barrier_profile, deck_length)

        # Relate barrier to the bridge
        run("spatial.assign_container", model, relating_structure=bridge, products=[barrier])

        return barrier

    # Set the left and right position for the two barrier using offsets
    left_barrier_y = barrier_offset + barrier_thickness/2
    right_barrier_y = deck_width - (barrier_offset + barrier_thickness/2)

    # Call make barrier function to create two barriers
    make_barrier("Left_Barrier", left_barrier_y)
    make_barrier("Right_Barrier", right_barrier_y)


    #11). Save the model
    # Write the model into the OUT_PATH IFC file
    model.write(OUT_PATH)
    return OUT_PATH

if __name__ == "__main__":
    # Quick local test
    demo = {}
    print("Created:", main(demo))














































































































































