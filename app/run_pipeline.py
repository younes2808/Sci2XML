import subprocess
import argparse
import sys

# Set up argument parsing
parser = argparse.ArgumentParser(description="Automate Sci2XML processing")

# Add arguments for each parameter
parser.add_argument('--nl_formula', type=str, choices=['True', 'False'], default='False', help="Set whether to use nl_formula (True/False). Defaults to False.")
parser.add_argument('--authtoken', type=str, required=True, help="Auth token for the ngrok tunnel")
parser.add_argument('--pdf', type=str, help="Path to the PDF file for processing (leave empty to process a folder)")
parser.add_argument('--output', type=str, help="Name of the output file (e.g., output.xml)")
parser.add_argument('--folder', type=str, help="Path to the folder (use this if not using a PDF)")

# Parse the arguments
args = parser.parse_args()

# Check if --authtoken is provided
if not args.authtoken:
    print("Error: --authtoken is required.")
    sys.exit(1)

# Check mutual exclusivity of --folder and --pdf + --output
if args.folder and (args.pdf or args.output):
    print("Error: If --folder is provided, --pdf and --output cannot be used.")
    sys.exit(1)
if args.pdf and not args.output:
    print("Error: --output must be provided when --pdf is used.")
    sys.exit(1)

# Set nl_formula to False if not given (already done by default='False' in argument parser)

# Step 1: Run the first script (launch_onlyAPI.py)
api_process = subprocess.Popen([
    "python", "Sci2XML/app/launch_onlyAPI.py", 
    "--tunnel", "ngrok", 
    "--port", "8001",
    "--nl_formula", args.nl_formula, 
    "--authtoken", args.authtoken
])

# Wait for the first process to finish
api_process.wait()

# Step 2: Run the second script (processing.py)
if args.pdf:
    # If a PDF file is provided, use the PDF-based command
    subprocess.run([
        "python", "Sci2XML/app/processing.py", 
        "--nl_formula", args.nl_formula, 
        "--pdf", args.pdf, 
        "--output", args.output
    ])
elif args.folder:
    # If no PDF is provided, use the folder-based command
    subprocess.run([
        "python", "Sci2XML/app/processing.py", 
        "--nl_formula", args.nl_formula, 
        "--folder", args.folder
    ])

print("Processing complete!")

