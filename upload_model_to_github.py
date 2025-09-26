from github import Github, Auth
from dotenv import load_dotenv
import os
import re

load_dotenv()

def get_latest_model_files(models_dir="models"):
    """
    Finds the latest .h5 and .keras model files based on the highest round number.
    """
    latest_round = -1
    latest_h5_file = None
    latest_keras_file = None

    for filename in os.listdir(models_dir):
        match = re.match(r"global_model_round_(\d+)\.(h5|keras)", filename)
        if match:
            round_num = int(match.group(1))
            file_extension = match.group(2)
            
            if round_num > latest_round:
                latest_round = round_num
                latest_h5_file = None  # Reset if a new higher round is found
                latest_keras_file = None

            if round_num == latest_round:
                full_path = os.path.join(models_dir, filename)
                if file_extension == "h5":
                    latest_h5_file = full_path
                elif file_extension == "keras":
                    latest_keras_file = full_path
    
    if latest_round == -1:
        print(f"No model files found in {models_dir}")
        return None, None
    
    print(f"Found latest model round: {latest_round}")
    return latest_h5_file, latest_keras_file

def upload_file_to_github(repo, file_path, github_path, commit_message):
    """
    Uploads a single file to GitHub.
    """
    with open(file_path, 'rb') as file_content:
        content = file_content.read()

    try:
        # Check if file exists to decide between update and create
        contents = repo.get_contents(github_path)
        repo.update_file(contents.path, commit_message, content, contents.sha)
        print(f"Updated {github_path} in {repo.full_name}")
    except Exception as e:
        repo.create_file(github_path, commit_message, content)
        print(f"Created {github_path} in {repo.full_name}")

def main():
    github_pat = os.getenv("GITHUB_PAT")
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name = os.getenv("GITHUB_REPO_NAME")
    github_branch = os.getenv("GITHUB_BRANCH", "main") # Default to 'main'
    github_target_folder = os.getenv("GITHUB_TARGET_FOLDER", "uploaded_models")

    if not all([github_pat, repo_owner, repo_name]):
        print("Error: Please set GITHUB_PAT, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME environment variables.")
        return

    g = Github(auth=Auth.Token(github_pat))
    try:
        repo = g.get_user(repo_owner).get_repo(repo_name)
    except Exception as e:
        print(f"Error accessing repository: {e}")
        print(f"Please ensure the repository '{repo_owner}/{repo_name}' exists and your PAT has appropriate permissions.")
        return

    latest_h5, latest_keras = get_latest_model_files()

    if latest_h5:
        h5_filename = os.path.basename(latest_h5)
        github_h5_path = f"{github_target_folder}/{h5_filename}"
        commit_message_h5 = f"Upload latest H5 model: {h5_filename}"
        upload_file_to_github(repo, latest_h5, github_h5_path, commit_message_h5)
    
    if latest_keras:
        keras_filename = os.path.basename(latest_keras)
        github_keras_path = f"{github_target_folder}/{keras_filename}"
        commit_message_keras = f"Upload latest Keras model: {keras_filename}"
        upload_file_to_github(repo, latest_keras, github_keras_path, commit_message_keras)
    
if __name__ == "__main__":
    main()
