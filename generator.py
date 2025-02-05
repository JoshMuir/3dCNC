import FreeCAD
import FreeCADGui
import Path
import PathScripts.PathJob as PathJob
import PathScripts.PathPost as PathPost
import Mesh
import math

def load_model(model_path):
    """
    Loads a 3D model (STL file) into a new document.
    """
    doc = FreeCAD.newDocument("CNC_Project")
    mesh_obj = doc.addObject("Mesh::Feature", "TargetMesh")
    mesh_obj.Mesh = Mesh.Mesh(model_path)
    doc.recompute()
    return doc, mesh_obj

def create_stock(doc, model_obj, margin=5.0):
    """
    Create a stock object using the model geometry expanded by a given margin.
    This defines the material boundaries for the machining process.
    """
    # We calculate the bounding box of the model
    bbox = model_obj.Shape.BoundBox
    # Stock dimensions with an extra margin (in mm) on all sides
    stock_x0 = bbox.XMin - margin
    stock_y0 = bbox.YMin - margin
    stock_z0 = bbox.ZMin - margin
    stock_x1 = bbox.XMax + margin
    stock_y1 = bbox.YMax + margin
    stock_z1 = bbox.ZMax + margin

    # Create a simple box representing the stock
    stock = FreeCAD.ActiveDocument.addObject("Part::Box", "Stock")
    stock.Length = stock_x1 - stock_x0
    stock.Width = stock_y1 - stock_y0
    stock.Height = stock_z1 - stock_z0
    stock.Placement.Base = FreeCAD.Vector(stock_x0, stock_y0, stock_z0)
    doc.recompute()
    return stock

def create_operation(job, op_type, tool, label, parameters):
    """
    Creates a machining operation in the job.
    op_type: a string to determine the type of operation (e.g., "PathPocket" for pocketing).
    tool: a tool name or ID defined in your tool library.
    label: a user-friendly label for the operation.
    parameters: a dictionary of additional operation parameters.
    """
    op = job.newOperation(op_type)
    op.Label = label
    op.Tool = tool

    # Update or set additional parameters provided in the dictionary.
    for param, value in parameters.items():
        try:
            setattr(op, param, value)
        except Exception as e:
            print(f"Could not set parameter {param} on {label}: {e}")

    FreeCAD.ActiveDocument.recompute()
    return op

def generate_toolpath(op):
    """
    Generate toolpath for a specific operation.
    """
    # Build the toolpath for the operation
    toolpath = op.buildPath()
    op.Job.Toolpath = toolpath
    FreeCAD.ActiveDocument.recompute()
    return toolpath

def export_gcode(job, output_file):
    """
    Export the generated toolpath as G-code using a post-processor.
    """
    post_processor = PathPost.PostProcessor()
    gcode = post_processor.export(job)
    with open(output_file, "w") as f:
        f.write(gcode)
    print("G-code exported to:", output_file)

def main():
    # Define paths
    model_path = "/path/to/your/model.stl"  # Replace with your model path
    output_gcode = "/path/to/your/output.gcode"  # Replace with desired output file path

    # Step 1: Load your 3D model
    doc, model_obj = load_model(model_path)

    # Step 2: Define the stock material (adding margin around the model)
    stock = create_stock(doc, model_obj, margin=5.0)

    # Step 3: Create a Path Job including the model and the stock.
    job = PathJob.Create("CNC_Job", [model_obj])
    job.Stock = stock  # Attach stock to the job
    doc.recompute()

    # Step 4: Create a roughing operation (e.g., pocketing for material removal)
    roughing_params = {
        "PocketStrategy": "Adaptive",  # Example strategy; adjust for your needs
        "StockMode": "BoundingBox",
        "StockClearance": 1.0,  # Clearance in mm
        "FeedRate": 1500
    }
    rough_op = create_operation(job, "PathPocket", "RoughingTool", "Roughing Operation", roughing_params)

    # Step 5: Generate toolpath for roughing
    print("Generating roughing toolpath...")
    generate_toolpath(rough_op)

    # Step 6: Create a finishing operation (to refine the surface)
    finishing_params = {
        "PocketStrategy": "ZigZag",  # Different strategy for a smoother surface
        "StockMode": "BoundingBox",
        "StockClearance": 0.5,  # Smaller clearance for finishing
        "FeedRate": 1200
    }
    finishing_op = create_operation(job, "PathPocket", "FinishingTool", "Finishing Operation", finishing_params)

    # Step 7: Generate toolpath for finishing
    print("Generating finishing toolpath...")
    generate_toolpath(finishing_op)

    # (Optional) Step 8: Simulate machining operations or visualize toolpaths in the GUI
    FreeCADGui.updateGui()

    # Step 9: Export the full toolpath as G-code
    export_gcode(job, output_gcode)

if __name__ == "__main__":
    main()