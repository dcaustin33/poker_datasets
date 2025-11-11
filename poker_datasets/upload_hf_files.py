from huggingface_hub import HfApi
import os

if __name__ == "__main__":
    path = ""
    for file in os.listdir(path):
        if file.endswith(".json"):
            name_in_repo = file
            api = HfApi()
            api.upload_file(
                path_or_fileobj=os.path.join(path, file),
                repo_id="",
                path_in_repo=name_in_repo,
                repo_type="dataset",
            )