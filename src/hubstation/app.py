"""Count a file """
import logging
from pathlib import Path

import settings


# Config root logger
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
)


def count_word(source_file: Path) -> None:
    """
    :param source_file:
    :return:    None
    """
    total_words = 0
    # Read source_file
    logging.debug('Read file: %s', source_file)
    with open(source_file, mode='r', encoding='utf-8') as source_obj:
        for line in source_obj.readlines():
            total_words += len(line.split(' '))
    logging.info('File has %s words', total_words)


def main():
    count_word(Path(settings.SOURCE_FILE))


if __name__ == '__main__':
    main()
