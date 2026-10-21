from unittest.mock import patch

import pytest

from src.capabilities.rag import retrieve


def test_unknown_concept_is_rejected():
    """Tuntematon taito ei saa käynnistää tietokantahakua."""
    with patch("src.capabilities.rag._get_collection") as collection:
        with pytest.raises(ValueError, match="Tuntematon taitotunniste"):
            retrieve("nonexistent_concept")

        collection.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_result_count_is_rejected(top_k):
    """Tulosten määrän pitää olla positiivinen."""
    with patch("src.capabilities.rag._get_collection") as collection:
        with pytest.raises(ValueError, match="top_k"):
            retrieve("chain_rule", top_k=top_k)

        collection.assert_not_called()