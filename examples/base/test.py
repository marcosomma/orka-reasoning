import orka.orka_cli

if __name__ == "__main__":
    # Path to your YAML orchestration config
    config_path = "example.yml"

    # Input to be passed to the orchestrator
    input_text = "What is the capital of France?"

    # Run the orchestrator with logging
    orka.orka_cli.run_cli_entrypoint(
        config_path=config_path,
        input_text=input_text,
        log_to_file=True
    )
