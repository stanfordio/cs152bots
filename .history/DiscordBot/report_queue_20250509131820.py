from collections import deque

class SubmittedReport:
    def __init__(self, id, author, content, type, subtype):
        self.author = author
        self.id = id
        self.content = content
        self.type = type
        self.subtype = subtype

class PriorityReportQueue:
    def __init__(self, num_levels):
        self.num_queues = num_levels
        self.queues = [deque() for _ in range(num_levels)]
    
    def enqueue(self, report, priority):
        if not (0 <= priority < len(self.queues)):
            raise ValueError("Invalid priority level")
        self.queues[priority].append(report)
    
    def dequeue(self):
        for queue in self.queues:
            if queue:
                return queue.popleft()
        raise IndexError("All queues are empty")
    
    def is_empty(self):
        return all(len(q) == 0 for q in self.queues)
    
    def __getitem__(self, priority):
        return list(self.queues[priority])
    
    def display(self):

