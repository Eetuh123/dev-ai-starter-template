from src.schemas.study import RagChunk, VerifierResult

def verify(content: str, chunks: list[RagChunk]) -> VerifierResult:
    return VerifierResult(passed=True)