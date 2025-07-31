from huggingface_hub import HfApi

if __name__ == "__main__":
    file = "/Users/derek/Desktop/poker_datasets/datasets/pluribus_all_narratives_it_test.json"
    name_in_repo = "pluribus_all_narratives_it_test.json"
    api = HfApi()
    api.upload_file(
        path_or_fileobj=file,
        repo_id="dcaustin33/poker_pretraining",
        path_in_repo=name_in_repo,
        repo_type="dataset",
    )