import subprocess
import argparse

def wait_for_launchoutput(process, ready_signal):
    """Wait until the LaunchOnlyAPI prints the ready message."""
    print("Waiting for LaunchOnlyAPI to be ready...")
    while True:
        line = process.stdout.readline()
        if not line:
            continue
        print(line.strip())
        if ready_signal in line:
            print("API is ready! Proceeding to processing.")
            break

def main():
    parser = argparse.ArgumentParser(description="Run LaunchOnlyAPI and then processing.py")
    parser.add_argument('--port', type=int, default=8001, help='Port for API')
    parser.add_argument('--authtoken', type=str, required=True, help='Auth token for API')
    parser.add_argument('--nl_formula', type=bool, default=False, help='Use natural language formula')
    parser.add_argument('--folder', type=str, help='Folder containing PDFs')
    parser.add_argument('--pdf', type=str, help='Single PDF file')
    parser.add_argument('--output', type=str, help='Output file name (XML)')

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
        text=True  # Text mode enabled to avoid RuntimeWarning
    )

    # 2. Wait for the API to be ready (look for the specific printed message)
    wait_for_launchoutput(launch_proc, "### User Interaction ###")

    # 3. Run processing.py with the correct arguments
    processing_cmd = ["python", "Sci2XML/app/processing.py"]

    processing_cmd += ["--nl_formula", str(args.nl_formula)]

    if args.folder:
        processing_cmd += ["--folder", args.folder]
    elif args.pdf and args.output:
        processing_cmd += ["--pdf", args.pdf, "--output", args.output]
    else:
        print("You must provide either --folder OR both --pdf and --output")
        return

    print(f"Running: {' '.join(processing_cmd)}")
    subprocess.run(processing_cmd)

if __name__ == "__main__":
    main()
