from src.schemas.study import RagChunk, VerifierResult


def verify(content: str, chunks: list[RagChunk]) -> VerifierResult:
    return VerifierResult(
        passed=False,
        issues=[
            "Automatic content verification is not implemented yet. "
            "The generated lesson may contain mathematical errors."
        ],
    )