from huggingface_hub import HfApi

if __name__ == "__main__":
    file = "/Users/derek/Desktop/poker_datasets/datasets/all_narratives_test.json"
    api = HfApi()
    api.upload_file(
        path_or_fileobj=file,
        repo_id="dcaustin33/poker_pretraining",
        path_in_repo="all_narratives_train.json",
        repo_type="dataset",
    )