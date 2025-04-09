import subprocess
import argparse
import os

def wait_for_launchoutput(process, ready_signal):
    """Wait until the LaunchOnlyAPI prints the ready message."""
    while True:
        line = process.stdout.readline()
        if not line:
            continue
        print(line.strip())
        if ready_signal in line:
            print("API is ready! Proceeding to CLI mode.")
            break

def process_pdf(args, pdf=None, folder=None, output=None):
    """Process PDF or folder with processing.py."""
    processing_cmd = ["python", "Sci2XML/app/processing.py"]
    processing_cmd += ["--nl_formula", str(args.nl_formula)]

    if folder:
        processing_cmd += ["--folder", folder]
    elif pdf and output:
        processing_cmd += ["--pdf", pdf, "--output", output]
    else:
        print("You must provide either --folder OR both --pdf and --output")
        return

    print(f"Running: {' '.join(processing_cmd)}")
    subprocess.run(processing_cmd)

def main():
    parser = argparse.ArgumentParser(description="Run LaunchOnlyAPI and then process multiple PDFs/folders.")
    parser.add_argument('--port', type=int, default=8001, help='Port for API')
    parser.add_argument('--authtoken', type=str, required=True, help='Auth token for API')
    parser.add_argument('--nl_formula', type=bool, default=False, help='Use natural language formula')

    args = parser.parse_args()

    # 1. Start LaunchOnlyAPI
    launch_cmd = [
        "python", "Sci2XML/app/launch_onlyAPI.py",
        "--port", str(args.port),
        "--authtoken", args.authtoken
    ]

    launch_proc = subprocess.Popen(
        launch_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True
    )

    try:
        # 2. Wait until API is ready
        wait_for_launchoutput(launch_proc, "### User Interaction ###")

        # 3. Start CLI loop
        while True:
            print("\nEnter a command to process a new PDF or folder, or type 'exit' to quit.")
            user_input = input("Command (folder/pdf/exit): ").strip().lower()

            if user_input == "exit":
                print("Exiting CLI. Shutting down API...")
                break

            elif user_input == "folder":
                folder_path = input("Enter the folder path: ").strip()
                if os.path.isdir(folder_path):
                    process_pdf(args, folder=folder_path)
                else:
                    print("Invalid folder path.")

            elif user_input == "pdf":
                pdf_file = input("Enter the PDF file path: ").strip()
                if os.path.isfile(pdf_file):
                    output_name = input("Enter the output XML filename: ").strip()
                    process_pdf(args, pdf=pdf_file, output=output_name)
                else:
                    print("Invalid PDF file.")

            else:
                print("Unknown command. Please enter 'folder', 'pdf', or 'exit'.")

    finally:
        print("Terminating LaunchOnlyAPI...")
        launch_proc.terminate()
        launch_proc.wait()
        print("API terminated. Goodbye!")

if __name__ == "__main__":
    main()
