"""Explicit extension points for work that needs people or external resources."""


def adjudicate_gold(annotation_exports, guidelines):
    """Produce adjudicated benchmark records after human review and resolution."""
    raise NotImplementedError("Gold adjudication requires independent annotations and human decisions.")


def link_concepts(records, vocabulary):
    """Attach stable concept IDs using a chosen, versioned vocabulary and policy."""
    raise NotImplementedError("Concept linking needs an agreed vocabulary and linking method.")


def predict_with_reference_entities(records, model):
    """Obtain relation predictions with supplied reference entities for oracle diagnostics."""
    raise NotImplementedError("Connect a model-specific oracle-entity interface before using this diagnostic.")
