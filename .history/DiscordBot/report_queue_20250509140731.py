from collections import deque

class SubmittedReport:
    def __init__(self, id, author, content, type, subtype):
        self.author = author
        self.id = id
        self.content = content
        self.type = type
        self.subtype = subtype

class PriorityReportQueue:
    def __init__(self, num_levels, queue_names):
        self.num_queues = num_levels
        self.queue_names = queue_names
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
    
    def summary(self):
        out = "```"
        out += "Priority |              Queue Name             | # Reports\n"
        out += "-" * 58 + "\n"
        total = 0
        for i in range(self.num_queues):
            queue = self.queues[i]
            out += f"{i:^8} | {self.queue_names[i]:<35} | {len(queue):^9}\n"
            total += len(queue)
        out += "-" * 58 + "\n"
        out += f"Total pending reports: {total}\n"
        out += "```"
        return out

    def display(self):
        out = ""
        for i in range(self.num_queues):
            queue = self.queues[i]
            out += f"--- Priority {i}: {self.queue_names[i]} ---\n"
            if not queue:
                out += "  (No reports)\n"
            else:
                for idx, report in enumerate(queue, 1):
                    out += (
                        f"  [{idx}] Report ID: {report.id}\n"
                        f"       Author: {report.author}\n"
                        f"       Type: {report.type}\n"
                        f"       Subtype: {report.subtype}\n"
                    )
                out += "\n"
        return out.strip()

