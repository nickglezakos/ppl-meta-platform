import asyncio
import numpy as np
import logging
import sys
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from services.embedding_service import EmbeddingService, DEEPFACE_AVAILABLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_embedding')

async def run_test():
    logger.info(f"DEEPFACE_AVAILABLE={DEEPFACE_AVAILABLE}")

    emb = EmbeddingService(database_client=None, config={})

    # Create a synthetic face-like image (random noise may help DeepFace avoid trivial failures)
    img = (np.random.rand(160, 160, 3) * 255).astype('uint8')

    try:
        # Call the internal wrapper which uses DeepFace.represent and may return
        # different shapes; we'll also call DeepFace.represent directly to inspect.
        embedding, confidence = await emb._generate_facial_embedding(
            img, 0, 0, img.shape[1], img.shape[0]
        )
        logger.info(
            f"Embedding (via _generate_facial_embedding): {type(embedding)} length={(len(embedding) if embedding else None)}"
        )
        logger.info(f"Confidence: {confidence}")

        # Inspect DeepFace.represent output directly for debugging
        try:
            from deepface import DeepFace

            repr_out = DeepFace.represent(
                img_path=img, model_name=emb.embedding_model, enforce_detection=False, detector_backend=emb.detector_backend
            )
            logger.info(f"DeepFace.represent type: {type(repr_out)}")
            logger.info(f"DeepFace.represent repr: {repr_out}")
        except Exception:
            logger.exception("Direct DeepFace.represent call failed")

    except Exception:
        logger.exception("Exception while generating embedding")

if __name__ == '__main__':
    asyncio.run(run_test())
