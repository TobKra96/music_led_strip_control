from multiprocess import Queue
import logging


class QueueWrapper():
    def __init__(self, queue):
        self.logger = logging.getLogger(__name__)
        self.queue = queue

    def put_blocking(self, element):
        self.queue.put(element, block=True)

    def put_none_blocking(self, element):
        if self.queue.full():
            self.__delete_last_element()
        self.queue.put(element, block=True, timeout=0.033)

    def get_blocking(self):
        return self.queue.get(block=True)

    def get_blocking_with_timeout(self):
        try:
            return self.queue.get(block=True, timeout=1)
        except Exception as e:
            self.logger.debug(f"Could not get item from queue: {str(e)}")
            return None

    def get_none_blocking(self):
        return self.queue.get(block=True, timeout=0.033)

    def empty(self):
        return self.queue.empty()

    def full(self):
        return self.queue.full()

    def __delete_last_element(self):
        try:
            delete_element = self.get_none_blocking()
            del delete_element
        except Exception as e:
            pass
