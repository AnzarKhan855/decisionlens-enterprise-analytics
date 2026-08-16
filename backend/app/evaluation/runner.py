from app.evaluation.framework import EvaluationFramework, run_evaluation
from app.evaluation.schemas import EvaluationConfig


def main():
    config = EvaluationConfig(
        datasets_dir="data/evaluation",
        output_dir="data/evaluation_results",
    )
    report = run_evaluation(config)
    return report


if __name__ == "__main__":
    main()