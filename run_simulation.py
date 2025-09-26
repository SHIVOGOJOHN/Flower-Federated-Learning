import subprocess
import time
import sys
import os
from upload_model_to_github import main as upload_main

def main():
    """
    This script launches the Flower server and three clients in separate console windows,
    redirecting their output to log files.
    """
    server_command = ["python", "server.py"]
    client_commands = [
        ("Client A", ["python", "client.py", "--store", "A"]),
        ("Client B", ["python", "client.py", "--store", "B"]),
        ("Client C", ["python", "client.py", "--store", "C"]),
    ]

    print("Starting the Federated Learning simulation...")
    print("Output of each process will be redirected to a log file.")

    # Create a directory for logs if it doesn't exist
    log_dir = "simulation_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    processes = []

    # Start the server
    server_log_path = os.path.join(log_dir, "server_log.txt")
    print(f"Starting Server. Output redirected to {server_log_path}...")
    with open(server_log_path, "w") as server_log_file:
        server_process = subprocess.Popen(
            server_command,
            stdout=server_log_file,
            stderr=subprocess.STDOUT # Redirect stderr to stdout
        )
        processes.append(server_process)
    print("Waiting 5 seconds for the server to initialize...")
    time.sleep(5)

    # Start the clients, staggered
    print("Starting clients...")
    for name, command in client_commands:
        client_log_path = os.path.join(log_dir, f"{name.replace(' ', '_').lower()}_log.txt")
        print(f"Starting {name}. Output redirected to {client_log_path}...")
        with open(client_log_path, "w") as client_log_file:
            proc = subprocess.Popen(
                command,
                stdout=client_log_file,
                stderr=subprocess.STDOUT # Redirect stderr to stdout
            )
            processes.append(proc)
        time.sleep(5) # Stagger client startups by 5 seconds

    print(f"\nAll processes launched. The simulation is running.")
    print("Waiting for the server to complete all federated learning rounds...")

    # Wait for the server process to terminate. The server will exit after all rounds are done.
    server_process.wait()
    print("\nServer has finished.")

    # Wait for all client processes to terminate
    print("Waiting for clients to terminate...")
    # The `processes` list contains the server process as the first element
    for proc in processes[1:]:
        proc.wait()
    print("All client processes have finished.")

    print("\nFederated Learning simulation complete.")
    print("----------------------------------------")
    print("Starting model upload to GitHub...")

    # Run the upload script
    try:
        upload_main()
        print("Upload script finished successfully.")
    except Exception as e:
        print(f"An error occurred during the upload process: {e}")

if __name__ == "__main__":
    main()