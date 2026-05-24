import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from scripts.run_training import main as run_training

    run_training()

    from backend.ml.config import BACKTEST_RESULTS_PATH
    from backend.notifications.telegram import TelegramNotifier

    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.info("No TELEGRAM_BOT_TOKEN set, skipping notification")
        return

    with open(BACKTEST_RESULTS_PATH) as f:
        results = json.load(f)

    notifier = TelegramNotifier()
    notifier.send_training_summary(results)
    logger.info("Training summary sent to %d chat(s)", len(notifier.chat_ids))


if __name__ == "__main__":
    main()
