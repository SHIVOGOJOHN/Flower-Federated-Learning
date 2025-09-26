import flwr as fl
import tensorflow as tf
from tensorflow.keras.layers import Dense, Input, Dropout
from tensorflow.keras.models import Sequential
import os
import json
from pathlib import Path
from datetime import datetime
from github import Github, Auth
import io
import random

LEDGER = Path('StreamlitBlockchainAI/ledger.json')
current_run_ledger_entries = []

def fake_ipfs_hash():
    return "Qm" + "".join(random.choices("0123456789abcdef", k=44))

def fake_tx_hash():
    return "0x" + "".join(random.choices("0123456789abcdef", k=64))

def append_to_local_ledger(round_num: int, global_accuracy: float, node_accuracies: dict, ipfs_hash: str, block_tx: str):
    global current_run_ledger_entries

    new_entry = {
        "round": round_num,
        "timestamp": datetime.now().isoformat(),
        "global_accuracy": global_accuracy,
        "ipfs_hash": ipfs_hash,
        "block_tx": block_tx,
        "notes": f"Aggregated metrics for round {round_num}",
        "node_accuracies": node_accuracies
    }
    current_run_ledger_entries.append(new_entry)

    with open(LEDGER, 'w') as f:
        json.dump(current_run_ledger_entries, f, indent=4)

def append_to_ledger(repo_owner: str, repo_name: str, github_file_path: str, github_branch: str = "main"):
    global current_run_ledger_entries

    github_pat = os.getenv("GITHUB_PAT_SERVER")

    if not github_pat:
        print(f"Error: GITHUB_PAT_SERVER not set in environment variables. Cannot update ledger on GitHub.")
        return False

    try:
        g = Github(auth=Auth.Token(github_pat))
        repo = g.get_user(repo_owner).get_repo(repo_name)
        
        new_json_content = json.dumps(current_run_ledger_entries, indent=4)
        
        contents = None
        try:
            contents = repo.get_contents(github_file_path, ref=github_branch)
        except Exception:
            pass

        commit_message = f"Update ledger with {len(current_run_ledger_entries)} entries from current server run"
        
        if contents:
            repo.update_file(contents.path, commit_message, new_json_content, contents.sha, branch=github_branch)
        else:
            repo.create_file(github_file_path, commit_message, new_json_content, branch=github_branch)

        print(f"Ledger updated on GitHub for {repo_owner}/{repo_name} with {len(current_run_ledger_entries)} entries.")
        return True
            
    except Exception as e:
        print(f"Error updating GitHub ledger for {repo_owner}/{repo_name}: {e}")
        return False

model = Sequential()

model = Sequential()
model.add(Input(shape=(20,)))
model.add(Dense(64, activation='relu')) # Hidden layer 1
model.add(Dropout(0.3)) # Dropout for regularization
model.add(Dense(32, activation='relu')) # Hidden layer 2
model.add(Dropout(0.3))
model.add(Dense(1, activation='sigmoid')) # Output layer
#model.add(Dense(1, activation='sigmoid', kernel_initializer='zeros', bias_initializer='zeros'))
model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=0.01),
                loss="binary_crossentropy",
                metrics=["accuracy"])

# Create a folder to save models
if not os.path.exists("models"):
    os.makedirs("models")

class SaveModelStrategy(fl.server.strategy.FedAvg):
    def aggregate_fit(
        self,
        server_round: int,
        results,
        failures,
    ):
        # Call aggregate_fit from base class (FedAvg) to aggregate parameters
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(server_round, results, failures)

        if aggregated_parameters is not None:
            # Convert `Parameters` to `List[np.ndarray]`
            aggregated_ndarrays = fl.common.parameters_to_ndarrays(aggregated_parameters)

            # Save the model
            print(f"Saving round {server_round} aggregated model...")
            model.set_weights(aggregated_ndarrays)
            model.save(f"models/global_model_round_{server_round}.keras")
            model.save(f"models/global_model_round_{server_round}.h5")

        return aggregated_parameters, aggregated_metrics

    def aggregate_evaluate(
        self,
        server_round: int,
        results,
        failures,
    ):
        if not results:
            return None, {}

        # Manually aggregate loss (weighted average)
        aggregated_loss = sum([r.loss * r.num_examples for _, r in results]) / sum([r.num_examples for _, r in results])
        
        # Manually aggregate accuracy (weighted average)
        accuracies = [r.metrics["accuracy"] * r.num_examples for _, r in results if r.metrics and "accuracy" in r.metrics]
        examples = [r.num_examples for _, r in results if r.metrics and "accuracy" in r.metrics]

        if not examples:
            # No clients returned accuracy
            global_accuracy = 0.0
            aggregated_metrics = {}
        else:
            global_accuracy = sum(accuracies) / sum(examples)
            aggregated_metrics = {"accuracy": global_accuracy}

        print(f"Round {server_round}: Aggregated Loss: {aggregated_loss}, Aggregated Metrics: {aggregated_metrics}")

        # Write global accuracy to file
        with open("accuracies.txt", "a") as f:
            f.write(f"{global_accuracy}\n")

        # Extract node accuracies for the ledger
        node_accuracies = {client.cid: res.metrics['accuracy'] for client, res in results if res.metrics and 'accuracy' in res.metrics}
        
        # Generate IPFS hash and blockchain transaction ID
        ipfs_hash = fake_ipfs_hash()
        block_tx = fake_tx_hash()

        append_to_local_ledger(server_round, global_accuracy, node_accuracies, ipfs_hash, block_tx)
        
        # GitHub logic
        ledger_repo_owner = os.getenv("GITHUB_LEDGER_REPO_OWNER")
        ledger_repo_name = os.getenv("GITHUB_LEDGER_REPO_NAME")
        ledger_file_path = os.getenv("GITHUB_LEDGER_FILE_PATH", "data/ledger.json")
        ledger_branch = os.getenv("GITHUB_LEDGER_BRANCH", "main")

        if ledger_repo_owner and ledger_repo_name:
            append_to_ledger(ledger_repo_owner, ledger_repo_name, ledger_file_path, ledger_branch)
        else:
            print("Warning: GITHUB_LEDGER_REPO_OWNER or GITHUB_LEDGER_REPO_NAME not set. Cannot update ledger on GitHub.")

        # Logic for a second ledger repository
        ledger_repo2_owner = os.getenv("GITHUB_LEDGER_REPO2_OWNER")
        ledger_repo2_name = os.getenv("GITHUB_LEDGER_REPO2_NAME")
        ledger_file2_path = os.getenv("GITHUB_LEDGER_FILE2_PATH", "data/ledger.json")
        ledger_branch2 = os.getenv("GITHUB_LEDGER_BRANCH2", "main")

        if ledger_repo2_owner and ledger_repo2_name:
            print(f"Attempting to update second ledger repository: {ledger_repo2_owner}/{ledger_repo2_name}")
            append_to_ledger(ledger_repo2_owner, ledger_repo2_name, ledger_file2_path, ledger_branch2)
        else:
            print("Warning: GITHUB_LEDGER_REPO2_OWNER or GITHUB_LEDGER_REPO2_NAME not set. Cannot update second ledger on GitHub.")

        return aggregated_loss, aggregated_metrics

# Define the strategy
strategy = SaveModelStrategy(
    initial_parameters=fl.common.ndarrays_to_parameters(model.get_weights()),
)

# Start the server
fl.server.start_server(server_address="0.0.0.0:8080", config=fl.server.ServerConfig(num_rounds=10), strategy=strategy)